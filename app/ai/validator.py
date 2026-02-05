# app/ai/validator.py
"""LangGraph-based claim validation agent."""

from typing import TypedDict, List, Dict, Any, Optional
from datetime import datetime
import asyncio
import time

from langgraph.graph import StateGraph, END

from app.ai.llm import get_llm_service
from app.ai.embeddings import get_embedding_service
from app.models.claim import (
    Claim, ClaimValidationResult, ValidationStep,
    PayoutCalculation, FraudAnalysis, FraudIndicator
)
from app.models.policy import Policy
from app.core.constants import FraudSeverity, FraudIndicatorType, ClaimStatus
from app.core.logging import get_logger
from app.core.exceptions import ClaimValidationError

logger = get_logger(__name__)


# ===================
# State Definition
# ===================

class ValidationState(TypedDict):
    """State for the validation workflow."""
    # Input
    claim: Dict[str, Any]
    policy: Dict[str, Any]
    
    # Retrieved context
    relevant_clauses: List[Dict[str, Any]]
    relevant_sources: List[Dict[str, Any]]
    
    # Analysis results
    coverage_analysis: Optional[Dict[str, Any]]
    exclusion_analysis: Optional[Dict[str, Any]]
    fraud_analysis: Optional[Dict[str, Any]]
    payout_calculation: Optional[Dict[str, Any]]
    
    # Validation steps
    steps: List[Dict[str, Any]]
    
    # Final result
    is_valid: bool
    recommendation: str
    confidence: float
    reasoning: str
    
    # Metadata
    errors: List[str]
    start_time: float


# ===================
# Validation Prompts
# ===================

COVERAGE_ANALYSIS_PROMPT = """Analyze if this claim is covered under the policy.

CLAIM:
- Type: {claim_type}
- Description: {claim_description}
- Amount: ${claimed_amount}
- Incident Date: {incident_date}

POLICY COVERAGE ITEMS:
{coverage_items}

RELEVANT POLICY CLAUSES:
{relevant_clauses}

Analyze:
1. Does any coverage item apply to this claim type?
2. Is the claim within the coverage limits?
3. Is the incident date within the policy period?
4. Are there any conditions that must be met?

Return JSON:
{{
  "coverage_applies": true/false,
  "matched_coverage_type": "coverage type that applies or null",
  "coverage_limit": 0,
  "deductible": 0,
  "copay_percentage": 0,
  "reasons": ["list of reasons"],
  "conditions_met": true/false,
  "confidence": 0.0-1.0
}}"""


EXCLUSION_ANALYSIS_PROMPT = """Check if any exclusions apply to this claim.

CLAIM:
- Type: {claim_type}
- Description: {claim_description}
- Incident Date: {incident_date}

POLICY EXCLUSIONS:
{exclusions}

For each exclusion, determine:
1. Does this exclusion apply to the claim?
2. Are there any exceptions that override the exclusion?

Return JSON:
{{
  "exclusions_triggered": [
    {{
      "exclusion_id": "id",
      "category": "category",
      "reason": "why it applies",
      "exception_applies": true/false,
      "exception_reason": "reason if exception applies"
    }}
  ],
  "claim_excluded": true/false,
  "confidence": 0.0-1.0
}}"""


RECOMMENDATION_PROMPT = """Based on the validation analysis, provide a final recommendation.

CLAIM:
- Type: {claim_type}
- Amount: ${claimed_amount}

COVERAGE ANALYSIS:
{coverage_analysis}

EXCLUSION ANALYSIS:
{exclusion_analysis}

FRAUD ANALYSIS:
{fraud_analysis}

PAYOUT CALCULATION:
{payout_calculation}

Provide a recommendation:
- "approve": Claim is valid and should be paid
- "deny": Claim is not covered or excluded
- "review": Needs manual review
- "investigate": Fraud indicators present

Return JSON:
{{
  "recommendation": "approve/deny/review/investigate",
  "confidence": 0.0-1.0,
  "reasoning_summary": "Brief summary of decision",
  "detailed_reasoning": "Detailed explanation"
}}"""


class ClaimValidator:
    """
    LangGraph-based claim validation agent.
    
    Workflow:
    1. Retrieve relevant policy information
    2. Check coverage applicability
    3. Check exclusions
    4. Detect fraud indicators
    5. Calculate payout
    6. Generate recommendation
    """
    
    def __init__(self):
        self.llm = get_llm_service()
        self.embeddings = get_embedding_service()
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the validation workflow graph."""
        workflow = StateGraph(ValidationState)
        
        # Add nodes
        workflow.add_node("retrieve_context", self._retrieve_context)
        workflow.add_node("analyze_coverage", self._analyze_coverage)
        workflow.add_node("analyze_exclusions", self._analyze_exclusions)
        workflow.add_node("detect_fraud", self._detect_fraud)
        workflow.add_node("calculate_payout", self._calculate_payout)
        workflow.add_node("generate_recommendation", self._generate_recommendation)
        
        # Define edges
        workflow.set_entry_point("retrieve_context")
        workflow.add_edge("retrieve_context", "analyze_coverage")
        workflow.add_edge("analyze_coverage", "analyze_exclusions")
        workflow.add_edge("analyze_exclusions", "detect_fraud")
        workflow.add_edge("detect_fraud", "calculate_payout")
        workflow.add_edge("calculate_payout", "generate_recommendation")
        workflow.add_edge("generate_recommendation", END)
        
        return workflow.compile()
    
    def _add_step(
        self, 
        state: ValidationState, 
        step_name: str, 
        status: str, 
        details: str = "",
        data: Dict = None
    ) -> ValidationState:
        """Add a validation step to state."""
        step = {
            "step_name": step_name,
            "status": status,
            "details": details,
            "data": data or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        state["steps"].append(step)
        return state
    
    async def _retrieve_context(self, state: ValidationState) -> Dict:
        """Retrieve relevant policy clauses using vector search."""
        claim = state["claim"]
        policy = state["policy"]
        
        # Build search query from claim
        search_query = f"{claim['claim_type']} {claim['incident']['description']}"
        
        try:
            # Search for relevant clauses
            results = await self.embeddings.similarity_search_async(
                query=search_query,
                k=5,
                filter={"policy_id": policy["policy_id"]}
            )
            
            state = self._add_step(
                state, "retrieve_context", "passed",
                f"Retrieved {len(results)} relevant clauses"
            )
            
            return {
                "relevant_sources": results,
                "relevant_clauses": [r["content"] for r in results],
                "steps": state["steps"]
            }
            
        except Exception as e:
            logger.error(f"Context retrieval failed: {e}")
            state = self._add_step(
                state, "retrieve_context", "warning",
                f"Limited context retrieved: {e}"
            )
            return {
                "relevant_sources": [],
                "relevant_clauses": [],
                "steps": state["steps"],
                "errors": state["errors"] + [str(e)]
            }
    
    async def _analyze_coverage(self, state: ValidationState) -> Dict:
        """Analyze if claim is covered under policy."""
        claim = state["claim"]
        policy = state["policy"]
        
        try:
            prompt = COVERAGE_ANALYSIS_PROMPT.format(
                claim_type=claim["claim_type"],
                claim_description=claim["incident"]["description"],
                claimed_amount=claim["claimed_amount"],
                incident_date=claim["incident"]["date"],
                coverage_items=policy.get("coverage_items", []),
                relevant_clauses=state.get("relevant_clauses", [])
            )
            
            result = await self.llm.invoke_with_json_async(prompt)
            
            status = "passed" if result.get("coverage_applies") else "failed"
            state = self._add_step(
                state, "coverage_analysis", status,
                f"Coverage {'applies' if result.get('coverage_applies') else 'does not apply'}",
                result
            )
            
            return {
                "coverage_analysis": result,
                "steps": state["steps"]
            }
            
        except Exception as e:
            logger.error(f"Coverage analysis failed: {e}")
            state = self._add_step(
                state, "coverage_analysis", "error", str(e)
            )
            return {
                "coverage_analysis": {"coverage_applies": False, "error": str(e)},
                "steps": state["steps"],
                "errors": state["errors"] + [str(e)]
            }
    
    async def _analyze_exclusions(self, state: ValidationState) -> Dict:
        """Check if any exclusions apply."""
        claim = state["claim"]
        policy = state["policy"]
        
        try:
            prompt = EXCLUSION_ANALYSIS_PROMPT.format(
                claim_type=claim["claim_type"],
                claim_description=claim["incident"]["description"],
                incident_date=claim["incident"]["date"],
                exclusions=policy.get("exclusions", [])
            )
            
            result = await self.llm.invoke_with_json_async(prompt)
            
            triggered = result.get("exclusions_triggered", [])
            status = "failed" if result.get("claim_excluded") else "passed"
            
            state = self._add_step(
                state, "exclusion_analysis", status,
                f"{len(triggered)} exclusions triggered" if triggered else "No exclusions apply",
                result
            )
            
            return {
                "exclusion_analysis": result,
                "steps": state["steps"]
            }
            
        except Exception as e:
            logger.error(f"Exclusion analysis failed: {e}")
            state = self._add_step(
                state, "exclusion_analysis", "error", str(e)
            )
            return {
                "exclusion_analysis": {"claim_excluded": False, "error": str(e)},
                "steps": state["steps"],
                "errors": state["errors"] + [str(e)]
            }
    
    async def _detect_fraud(self, state: ValidationState) -> Dict:
        """Detect potential fraud indicators."""
        claim = state["claim"]
        policy = state["policy"]
        
        indicators = []
        fraud_score = 0.0
        
        # Rule 1: Claim submitted too soon after policy start
        # (This would need actual date comparison logic)
        
        # Rule 2: High value claim
        if claim["claimed_amount"] > 50000:
            indicators.append({
                "indicator_type": FraudIndicatorType.AMOUNT_ANOMALY.value,
                "severity": FraudSeverity.MEDIUM.value,
                "description": "High value claim",
                "score_contribution": 0.2
            })
            fraud_score += 0.2
        
        # Rule 3: Vague description
        if len(claim["incident"]["description"]) < 50:
            indicators.append({
                "indicator_type": FraudIndicatorType.INCONSISTENT_INFO.value,
                "severity": FraudSeverity.LOW.value,
                "description": "Vague incident description",
                "score_contribution": 0.1
            })
            fraud_score += 0.1
        
        # Determine risk level
        if fraud_score >= 0.7:
            risk_level = FraudSeverity.HIGH.value
        elif fraud_score >= 0.5:
            risk_level = FraudSeverity.MEDIUM.value
        else:
            risk_level = FraudSeverity.LOW.value
        
        fraud_analysis = {
            "fraud_score": min(fraud_score, 1.0),
            "risk_level": risk_level,
            "requires_investigation": fraud_score >= 0.5,
            "indicators": indicators
        }
        
        status = "warning" if fraud_score >= 0.5 else "passed"
        state = self._add_step(
            state, "fraud_detection", status,
            f"Fraud score: {fraud_score:.2f}",
            fraud_analysis
        )
        
        return {
            "fraud_analysis": fraud_analysis,
            "steps": state["steps"]
        }
    
    async def _calculate_payout(self, state: ValidationState) -> Dict:
        """Calculate recommended payout amount."""
        claim = state["claim"]
        coverage_analysis = state.get("coverage_analysis", {})
        exclusion_analysis = state.get("exclusion_analysis", {})
        
        claimed_amount = claim["claimed_amount"]
        
        # If not covered or excluded, payout is 0
        if not coverage_analysis.get("coverage_applies") or exclusion_analysis.get("claim_excluded"):
            payout_calculation = {
                "claimed_amount": claimed_amount,
                "eligible_amount": 0,
                "coverage_limit": 0,
                "deductible": 0,
                "copay_amount": 0,
                "recommended_payout": 0,
                "notes": ["Claim not eligible for payout"]
            }
        else:
            coverage_limit = coverage_analysis.get("coverage_limit", 0)
            deductible = coverage_analysis.get("deductible", 0)
            copay_pct = coverage_analysis.get("copay_percentage", 0)
            
            # Calculate
            eligible = min(claimed_amount, coverage_limit) if coverage_limit > 0 else claimed_amount
            after_deductible = max(0, eligible - deductible)
            copay_amount = after_deductible * (copay_pct / 100) if copay_pct else 0
            recommended_payout = after_deductible - copay_amount
            
            payout_calculation = {
                "claimed_amount": claimed_amount,
                "eligible_amount": eligible,
                "coverage_limit": coverage_limit,
                "deductible": deductible,
                "copay_amount": round(copay_amount, 2),
                "recommended_payout": round(recommended_payout, 2),
                "breakdown": {
                    "claimed": claimed_amount,
                    "coverage_limit_applied": eligible,
                    "less_deductible": -deductible,
                    "less_copay": -round(copay_amount, 2),
                    "total": round(recommended_payout, 2)
                },
                "notes": []
            }
        
        state = self._add_step(
            state, "payout_calculation", "passed",
            f"Recommended payout: ${payout_calculation['recommended_payout']}",
            payout_calculation
        )
        
        return {
            "payout_calculation": payout_calculation,
            "steps": state["steps"]
        }
    
    async def _generate_recommendation(self, state: ValidationState) -> Dict:
        """Generate final recommendation."""
        coverage_analysis = state.get("coverage_analysis", {})
        exclusion_analysis = state.get("exclusion_analysis", {})
        fraud_analysis = state.get("fraud_analysis", {})
        payout_calculation = state.get("payout_calculation", {})
        
        try:
            prompt = RECOMMENDATION_PROMPT.format(
                claim_type=state["claim"]["claim_type"],
                claimed_amount=state["claim"]["claimed_amount"],
                coverage_analysis=coverage_analysis,
                exclusion_analysis=exclusion_analysis,
                fraud_analysis=fraud_analysis,
                payout_calculation=payout_calculation
            )
            
            result = await self.llm.invoke_with_json_async(prompt)
            
            return {
                "is_valid": coverage_analysis.get("coverage_applies", False) and not exclusion_analysis.get("claim_excluded", False),
                "recommendation": result.get("recommendation", "review"),
                "confidence": result.get("confidence", 0.5),
                "reasoning": result.get("reasoning_summary", ""),
                "steps": state["steps"]
            }
            
        except Exception as e:
            logger.error(f"Recommendation generation failed: {e}")
            
            # Fallback logic
            if fraud_analysis.get("requires_investigation"):
                recommendation = "investigate"
            elif not coverage_analysis.get("coverage_applies"):
                recommendation = "deny"
            elif exclusion_analysis.get("claim_excluded"):
                recommendation = "deny"
            else:
                recommendation = "review"
            
            return {
                "is_valid": False,
                "recommendation": recommendation,
                "confidence": 0.5,
                "reasoning": "Automated fallback decision",
                "steps": state["steps"],
                "errors": state["errors"] + [str(e)]
            }
    
    async def validate(self, claim: Claim, policy: Policy) -> ClaimValidationResult:
        """
        Run the complete validation workflow.
        
        Args:
            claim: The claim to validate
            policy: The associated policy
        
        Returns:
            ClaimValidationResult with full analysis
        """
        logger.info(f"Starting validation for claim {claim.claim_id}")
        start_time = time.time()
        
        # Initialize state
        initial_state: ValidationState = {
            "claim": claim.model_dump(mode='json'),
            "policy": policy.model_dump(mode='json'),
            "relevant_clauses": [],
            "relevant_sources": [],
            "coverage_analysis": None,
            "exclusion_analysis": None,
            "fraud_analysis": None,
            "payout_calculation": None,
            "steps": [],
            "is_valid": False,
            "recommendation": "pending",
            "confidence": 0.0,
            "reasoning": "",
            "errors": [],
            "start_time": start_time
        }
        
        # Run the workflow
        try:
            final_state = await self.graph.ainvoke(initial_state)
        except Exception as e:
            logger.error(f"Validation workflow failed: {e}")
            raise ClaimValidationError(str(e), claim.claim_id)
        
        processing_time = (time.time() - start_time) * 1000
        
        # Build validation result
        from app.models.base import generate_id
        
        # Convert fraud analysis
        fraud_analysis = None
        if final_state.get("fraud_analysis"):
            fa = final_state["fraud_analysis"]
            fraud_analysis = FraudAnalysis(
                fraud_score=fa.get("fraud_score", 0),
                risk_level=FraudSeverity(fa.get("risk_level", "low")),
                requires_investigation=fa.get("requires_investigation", False),
                indicators=[
                    FraudIndicator(**i) for i in fa.get("indicators", [])
                ]
            )
        
        # Convert payout calculation
        payout_calculation = None
        if final_state.get("payout_calculation"):
            payout_calculation = PayoutCalculation(**final_state["payout_calculation"])
        
        # Convert validation steps
        validation_steps = [
            ValidationStep(**s) for s in final_state.get("steps", [])
        ]
        
        result = ClaimValidationResult(
            validation_id=generate_id("val"),
            is_valid=final_state.get("is_valid", False),
            recommendation=final_state.get("recommendation", "review"),
            confidence_score=final_state.get("confidence", 0.5),
            coverage_applies=final_state.get("coverage_analysis", {}).get("coverage_applies", False),
            matched_coverage=final_state.get("coverage_analysis"),
            exclusions_triggered=[
                e["exclusion_id"] for e in 
                final_state.get("exclusion_analysis", {}).get("exclusions_triggered", [])
            ],
            exclusion_details=final_state.get("exclusion_analysis", {}).get("exclusions_triggered", []),
            payout_calculation=payout_calculation,
            fraud_analysis=fraud_analysis,
            validation_steps=validation_steps,
            relevant_clauses=final_state.get("relevant_clauses", []),
            relevant_sources=final_state.get("relevant_sources", []),
            reasoning_summary=final_state.get("reasoning", ""),
            processing_time_ms=processing_time,
            model_used=self.llm.provider_name
        )
        
        logger.info(
            f"Validation complete for {claim.claim_id}: "
            f"recommendation={result.recommendation}, confidence={result.confidence_score}"
        )
        
        return result


# Singleton instance
_validator: Optional[ClaimValidator] = None


def get_claim_validator() -> ClaimValidator:
    """Get the claim validator singleton."""
    global _validator
    if _validator is None:
        _validator = ClaimValidator()
    return _validator