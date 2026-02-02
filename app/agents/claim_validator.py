# app/agents/claim_validator.py
from typing import TypedDict, Annotated, Literal
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage, AIMessage
from langchain_huggingface import HuggingFaceEndpoint
from app.models.claim import Claim, ClaimValidationResult
from app.database.neo4j_client import Neo4jClient
from app.database.pinecone_client import PineconeClient

# State definition
class ClaimValidationState(TypedDict):
    claim: Claim
    policy_id: str
    
    # Retrieved information
    relevant_clauses: list[dict]
    applicable_coverage: list[dict]
    potential_exclusions: list[dict]
    similar_claims: list[dict]
    
    # Validation results
    coverage_check: dict | None
    exclusion_check: dict | None
    fraud_check: dict | None
    
    # Final result
    validation_result: ClaimValidationResult | None
    messages: list

class ClaimValidatorAgent:
    """LangGraph-based claim validation workflow."""
    
    def __init__(
        self,
        neo4j_client: Neo4jClient,
        pinecone_client: PineconeClient,
        model_name: str = "mistralai/Mixtral-8x7B-Instruct-v0.1"
    ):
        self.neo4j = neo4j_client
        self.pinecone = pinecone_client
        self.llm = HuggingFaceEndpoint(
            repo_id=model_name,
            temperature=0.1,
            max_new_tokens=2048
        )
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the claim validation workflow graph."""
        
        workflow = StateGraph(ClaimValidationState)
        
        # Add nodes
        workflow.add_node("retrieve_policy_info", self._retrieve_policy_info)
        workflow.add_node("check_coverage", self._check_coverage)
        workflow.add_node("check_exclusions", self._check_exclusions)
        workflow.add_node("check_fraud", self._check_fraud)
        workflow.add_node("calculate_payout", self._calculate_payout)
        workflow.add_node("generate_result", self._generate_result)
        
        # Define edges
        workflow.set_entry_point("retrieve_policy_info")
        workflow.add_edge("retrieve_policy_info", "check_coverage")
        workflow.add_edge("check_coverage", "check_exclusions")
        workflow.add_edge("check_exclusions", "check_fraud")
        workflow.add_edge("check_fraud", "calculate_payout")
        workflow.add_edge("calculate_payout", "generate_result")
        workflow.add_edge("generate_result", END)
        
        return workflow.compile()
    
    async def _retrieve_policy_info(self, state: ClaimValidationState) -> dict:
        """Retrieve relevant policy information from Neo4j and Pinecone."""
        
        claim = state["claim"]
        policy_id = state["policy_id"]
        
        # Get structured data from Neo4j
        applicable_coverage = await self.neo4j.find_applicable_coverage(
            policy_id, 
            claim.claim_type.value
        )
        
        potential_exclusions = await self.neo4j.find_exclusions_for_claim(
            policy_id,
            claim.description
        )
        
        # Get relevant clauses from Pinecone (semantic search)
        relevant_docs = await self.pinecone.similarity_search(
            query=f"{claim.claim_type.value}: {claim.description}",
            filter={"policy_id": policy_id},
            k=5
        )
        relevant_clauses = [
            {"content": doc.page_content, "metadata": doc.metadata}
            for doc in relevant_docs
        ]
        
        return {
            "applicable_coverage": applicable_coverage,
            "potential_exclusions": potential_exclusions,
            "relevant_clauses": relevant_clauses,
            "messages": state["messages"] + [
                AIMessage(content=f"Retrieved {len(relevant_clauses)} relevant clauses")
            ]
        }
    
    async def _check_coverage(self, state: ClaimValidationState) -> dict:
        """Determine if claim is covered under policy."""
        
        claim = state["claim"]
        coverage = state["applicable_coverage"]
        clauses = state["relevant_clauses"]
        
        prompt = f"""Analyze if this claim is covered under the policy.

CLAIM:
- Type: {claim.claim_type.value}
- Description: {claim.description}
- Amount: ${claim.claimed_amount}
- Incident Date: {claim.incident_date}

APPLICABLE COVERAGE:
{coverage}

RELEVANT POLICY CLAUSES:
{clauses}

Determine:
1. Is this type of claim covered? (yes/no)
2. Which specific coverage applies?
3. What is the coverage limit?
4. What is the deductible?
5. Confidence score (0-1)

Return as JSON."""

        response = await self.llm.ainvoke(prompt)
        
        # Parse response (simplified - add proper JSON parsing)
        coverage_check = {
            "is_covered": True,  # Parse from response
            "coverage_type": coverage[0]["coverage_type"] if coverage else None,
            "limit": coverage[0]["limit_amount"] if coverage else 0,
            "deductible": coverage[0]["deductible"] if coverage else 0,
            "reasoning": response,
            "confidence": 0.85
        }
        
        return {
            "coverage_check": coverage_check,
            "messages": state["messages"] + [
                AIMessage(content=f"Coverage check: {'Covered' if coverage_check['is_covered'] else 'Not covered'}")
            ]
        }
    
    async def _check_exclusions(self, state: ClaimValidationState) -> dict:
        """Check if any exclusions apply to the claim."""
        
        claim = state["claim"]
        exclusions = state["potential_exclusions"]
        
        prompt = f"""Analyze if any exclusions apply to this claim.

CLAIM:
- Type: {claim.claim_type.value}
- Description: {claim.description}
- Incident Date: {claim.incident_date}

POLICY EXCLUSIONS:
{exclusions}

For each exclusion, determine:
1. Does this exclusion apply? (yes/no)
2. Why or why not?
3. Are there any exceptions that override the exclusion?

Return as JSON with list of triggered exclusions."""

        response = await self.llm.ainvoke(prompt)
        
        exclusion_check = {
            "exclusions_triggered": [],  # Parse from response
            "reasoning": response,
            "has_exceptions": False
        }
        
        return {
            "exclusion_check": exclusion_check,
            "messages": state["messages"] + [
                AIMessage(content=f"Exclusion check: {len(exclusion_check['exclusions_triggered'])} exclusions triggered")
            ]
        }
    
    async def _check_fraud(self, state: ClaimValidationState) -> dict:
        """Run fraud detection checks."""
        
        claim = state["claim"]
        
        # Get similar past claims for pattern matching
        similar_claims = await self.pinecone.similarity_search(
            query=claim.description,
            filter={"type": "claim"},
            k=10
        )
        
        fraud_indicators = []
        fraud_score = 0.0
        
        # Rule-based checks
        # 1. Check claim timing (claims right after policy start)
        # 2. Check claim amount vs typical claims
        # 3. Check for duplicate descriptions
        # 4. Check claim frequency
        
        prompt = f"""Analyze this claim for potential fraud indicators.

CLAIM:
- Type: {claim.claim_type.value}
- Description: {claim.description}
- Amount: ${claim.claimed_amount}
- Incident Date: {claim.incident_date}
- Submission Date: {claim.submission_date}

SIMILAR PAST CLAIMS:
{[doc.page_content for doc in similar_claims[:5]]}

Check for:
1. Unusually high amount for this claim type
2. Vague or inconsistent description
3. Timing anomalies
4. Similarity to known fraudulent patterns
5. Multiple claims for same incident

Return fraud indicators as JSON with severity (low/medium/high)."""

        response = await self.llm.ainvoke(prompt)
        
        fraud_check = {
            "fraud_indicators": fraud_indicators,
            "fraud_score": fraud_score,
            "reasoning": response,
            "requires_investigation": fraud_score > 0.5
        }
        
        return {
            "fraud_check": fraud_check,
            "similar_claims": [
                {"content": doc.page_content} for doc in similar_claims
            ],
            "messages": state["messages"] + [
                AIMessage(content=f"Fraud score: {fraud_score}")
            ]
        }
    
    async def _calculate_payout(self, state: ClaimValidationState) -> dict:
        """Calculate recommended payout amount."""
        
        claim = state["claim"]
        coverage_check = state["coverage_check"]
        exclusion_check = state["exclusion_check"]
        fraud_check = state["fraud_check"]
        
        if not coverage_check["is_covered"]:
            return {"recommended_payout": 0}
        
        if exclusion_check["exclusions_triggered"]:
            return {"recommended_payout": 0}
        
        if fraud_check["requires_investigation"]:
            return {"recommended_payout": 0, "status": "pending_investigation"}
        
        # Calculate payout
        claimed = claim.claimed_amount
        limit = coverage_check["limit"]
        deductible = coverage_check["deductible"]
        
        payout = min(claimed, limit) - deductible
        payout = max(0, payout)  # Can't be negative
        
        return {
            "recommended_payout": payout,
            "messages": state["messages"] + [
                AIMessage(content=f"Recommended payout: ${payout}")
            ]
        }
    
    async def _generate_result(self, state: ClaimValidationState) -> dict:
        """Generate final validation result."""
        
        claim = state["claim"]
        coverage_check = state["coverage_check"]
        exclusion_check = state["exclusion_check"]
        fraud_check = state["fraud_check"]
        
        result = ClaimValidationResult(
            claim_id=claim.claim_id,
            is_valid=coverage_check["is_covered"] and not exclusion_check["exclusions_triggered"],
            coverage_applies=coverage_check["is_covered"],
            exclusions_triggered=exclusion_check["exclusions_triggered"],
            coverage_limit=coverage_check.get("limit", 0),
            deductible=coverage_check.get("deductible", 0),
            recommended_payout=state.get("recommended_payout", 0),
            validation_steps=[
                {"step": "coverage_check", "result": coverage_check},
                {"step": "exclusion_check", "result": exclusion_check},
                {"step": "fraud_check", "result": fraud_check}
            ],
            relevant_clauses=[c["content"] for c in state["relevant_clauses"]],
            confidence_score=coverage_check.get("confidence", 0),
            fraud_flags=[f["description"] for f in fraud_check["fraud_indicators"]],
            fraud_risk_score=fraud_check["fraud_score"]
        )
        
        return {"validation_result": result}
    
    async def validate_claim(self, claim: Claim, policy_id: str) -> ClaimValidationResult:
        """Run full claim validation workflow."""
        
        initial_state = ClaimValidationState(
            claim=claim,
            policy_id=policy_id,
            relevant_clauses=[],
            applicable_coverage=[],
            potential_exclusions=[],
            similar_claims=[],
            coverage_check=None,
            exclusion_check=None,
            fraud_check=None,
            validation_result=None,
            messages=[HumanMessage(content=f"Validate claim {claim.claim_id}")]
        )
        
        final_state = await self.graph.ainvoke(initial_state)
        return final_state["validation_result"]