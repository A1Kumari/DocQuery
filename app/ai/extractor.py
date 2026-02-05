# app/ai/extractor.py
"""Policy extraction service using LLM."""

from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncio
import time

from app.ai.llm import get_llm_service
from app.models.policy import (
    Policy, Clause, CoverageItem, Exclusion, 
    ExtractionMetadata, PolicyHolder
)
from app.core.constants import ClauseType, PolicyType
from app.core.logging import get_logger
from app.core.exceptions import PolicyExtractionError

logger = get_logger(__name__)


# ===================
# Extraction Prompts
# ===================

CLAUSE_EXTRACTION_PROMPT = """Analyze this insurance policy document and extract ALL clauses.

DOCUMENT TEXT:
{text}

For each clause found, provide:
1. clause_type: One of: coverage, exclusion, condition, limitation, definition, procedure
2. title: Brief descriptive title
3. description: Full text of the clause
4. section_reference: Section number if mentioned (e.g., "Section 4.2")
5. page_number: Page number if identifiable
6. conditions: List of conditions that apply to this clause
7. keywords: Key terms in this clause

Return a JSON array of clauses. Example format:
[
  {{
    "clause_type": "coverage",
    "title": "Hospitalization Coverage",
    "description": "Full clause text here...",
    "section_reference": "Section 4.2",
    "page_number": 12,
    "conditions": ["Must be medically necessary"],
    "keywords": ["hospitalization", "inpatient", "room and board"]
  }}
]

Extract ALL clauses you can find. Be thorough."""


COVERAGE_EXTRACTION_PROMPT = """Extract ALL coverage limits and financial terms from this insurance policy.

DOCUMENT TEXT:
{text}

For each coverage item, extract:
1. coverage_type: What is covered (e.g., "hospitalization", "surgery", "medication")
2. description: Description of what's covered
3. limit_amount: Maximum coverage amount (number only, 0 if not specified)
4. deductible: Deductible amount (number only, 0 if not specified)
5. copay_percentage: Copay percentage if mentioned (0-100)
6. per_incident: Is this per incident? (true/false)
7. annual_aggregate: Annual maximum if mentioned
8. waiting_period_days: Waiting period in days (0 if none)
9. requires_preauthorization: Does this require pre-approval? (true/false)

Return a JSON array. Example:
[
  {{
    "coverage_type": "hospitalization",
    "description": "Inpatient hospital room and board",
    "limit_amount": 50000,
    "deductible": 500,
    "copay_percentage": 20,
    "per_incident": true,
    "annual_aggregate": 100000,
    "waiting_period_days": 30,
    "requires_preauthorization": false
  }}
]

Extract ALL coverage items with their limits."""


EXCLUSION_EXTRACTION_PROMPT = """Extract ALL exclusions from this insurance policy.
Exclusions are conditions, situations, or treatments that are NOT covered.

DOCUMENT TEXT:
{text}

For each exclusion, extract:
1. category: Category of exclusion (e.g., "pre-existing conditions", "cosmetic procedures", "experimental treatment")
2. description: Full description of what is excluded
3. keywords: Key terms to identify this exclusion
4. exceptions: Any exceptions where this exclusion does NOT apply
5. severity: "standard" or "absolute" (absolute means no exceptions)

Return a JSON array. Example:
[
  {{
    "category": "pre-existing conditions",
    "description": "Any condition diagnosed or treated within 24 months before the policy effective date",
    "keywords": ["pre-existing", "prior condition", "previous diagnosis"],
    "exceptions": ["Conditions disclosed and accepted during underwriting"],
    "severity": "standard"
  }}
]

Extract ALL exclusions comprehensively."""


class PolicyExtractor:
    """
    Extract structured information from insurance policy documents.
    Uses LLM for intelligent extraction of clauses, coverage, and exclusions.
    """
    
    def __init__(self):
        self.llm = get_llm_service()
        self.extraction_version = "1.0"
    
    async def extract_clauses(self, text: str) -> List[Clause]:
        """Extract all clauses from policy text."""
        logger.info("Extracting clauses from policy text...")
        
        try:
            result = await self.llm.invoke_with_json_async(
                CLAUSE_EXTRACTION_PROMPT.format(text=text[:15000])  # Limit text length
            )
            
            clauses = []
            for item in result:
                try:
                    clause_type = item.get("clause_type", "coverage").lower()
                    if clause_type not in ClauseType.values():
                        clause_type = "coverage"
                    
                    clause = Clause(
                        clause_type=ClauseType(clause_type),
                        title=item.get("title", "Untitled Clause"),
                        description=item.get("description", ""),
                        section_reference=item.get("section_reference"),
                        page_number=item.get("page_number"),
                        conditions=item.get("conditions", []),
                        keywords=item.get("keywords", []),
                        confidence_score=0.85  # Default confidence
                    )
                    clauses.append(clause)
                except Exception as e:
                    logger.warning(f"Failed to parse clause: {e}")
                    continue
            
            logger.info(f"Extracted {len(clauses)} clauses")
            return clauses
            
        except Exception as e:
            logger.error(f"Clause extraction failed: {e}")
            raise PolicyExtractionError(f"Failed to extract clauses: {e}")
    
    async def extract_coverage(self, text: str) -> List[CoverageItem]:
        """Extract coverage limits and details."""
        logger.info("Extracting coverage items from policy text...")
        
        try:
            result = await self.llm.invoke_with_json_async(
                COVERAGE_EXTRACTION_PROMPT.format(text=text[:15000])
            )
            
            coverage_items = []
            for item in result:
                try:
                    coverage = CoverageItem(
                        coverage_type=item.get("coverage_type", "general"),
                        description=item.get("description", ""),
                        limit_amount=float(item.get("limit_amount", 0)),
                        deductible=float(item.get("deductible", 0)),
                        copay_percentage=item.get("copay_percentage"),
                        per_incident=item.get("per_incident", True),
                        annual_aggregate=item.get("annual_aggregate"),
                        waiting_period_days=int(item.get("waiting_period_days", 0)),
                        requires_preauthorization=item.get("requires_preauthorization", False)
                    )
                    coverage_items.append(coverage)
                except Exception as e:
                    logger.warning(f"Failed to parse coverage item: {e}")
                    continue
            
            logger.info(f"Extracted {len(coverage_items)} coverage items")
            return coverage_items
            
        except Exception as e:
            logger.error(f"Coverage extraction failed: {e}")
            raise PolicyExtractionError(f"Failed to extract coverage: {e}")
    
    async def extract_exclusions(self, text: str) -> List[Exclusion]:
        """Extract all exclusions from policy."""
        logger.info("Extracting exclusions from policy text...")
        
        try:
            result = await self.llm.invoke_with_json_async(
                EXCLUSION_EXTRACTION_PROMPT.format(text=text[:15000])
            )
            
            exclusions = []
            for item in result:
                try:
                    exclusion = Exclusion(
                        category=item.get("category", "general"),
                        description=item.get("description", ""),
                        keywords=item.get("keywords", []),
                        exceptions=item.get("exceptions", []),
                        severity=item.get("severity", "standard"),
                        confidence_score=0.85
                    )
                    exclusions.append(exclusion)
                except Exception as e:
                    logger.warning(f"Failed to parse exclusion: {e}")
                    continue
            
            logger.info(f"Extracted {len(exclusions)} exclusions")
            return exclusions
            
        except Exception as e:
            logger.error(f"Exclusion extraction failed: {e}")
            raise PolicyExtractionError(f"Failed to extract exclusions: {e}")
    
    async def extract_full_policy(
        self,
        text: str,
        policy_number: str,
        policy_type: PolicyType,
        holder: PolicyHolder,
        effective_date,
        expiration_date,
        source_filename: Optional[str] = None
    ) -> Policy:
        """
        Perform complete policy extraction.
        
        Extracts clauses, coverage items, and exclusions in parallel.
        """
        logger.info(f"Starting full policy extraction for {policy_number}")
        start_time = time.time()
        
        warnings = []
        errors = []
        
        # Run extractions in parallel
        try:
            clauses_task = self.extract_clauses(text)
            coverage_task = self.extract_coverage(text)
            exclusions_task = self.extract_exclusions(text)
            
            clauses, coverage_items, exclusions = await asyncio.gather(
                clauses_task,
                coverage_task,
                exclusions_task,
                return_exceptions=True
            )
            
            # Handle any exceptions
            if isinstance(clauses, Exception):
                errors.append(f"Clause extraction failed: {clauses}")
                clauses = []
            
            if isinstance(coverage_items, Exception):
                errors.append(f"Coverage extraction failed: {coverage_items}")
                coverage_items = []
            
            if isinstance(exclusions, Exception):
                errors.append(f"Exclusion extraction failed: {exclusions}")
                exclusions = []
                
        except Exception as e:
            logger.error(f"Policy extraction failed: {e}")
            raise PolicyExtractionError(str(e))
        
        processing_time = (time.time() - start_time) * 1000
        
        # Calculate overall confidence
        all_confidences = (
            [c.confidence_score for c in clauses] +
            [e.confidence_score for e in exclusions]
        )
        overall_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0
        
        # Create extraction metadata
        extraction_metadata = ExtractionMetadata(
            model_used=self.llm.provider_name,
            extraction_version=self.extraction_version,
            total_pages=0,  # Will be set by document processor
            processing_time_ms=processing_time,
            overall_confidence=overall_confidence,
            warnings=warnings,
            errors=errors
        )
        
        # Create policy
        from app.models.base import generate_id
        
        policy = Policy(
            policy_id=generate_id("pol"),
            policy_number=policy_number,
            policy_type=policy_type,
            holder=holder,
            effective_date=effective_date,
            expiration_date=expiration_date,
            clauses=clauses,
            coverage_items=coverage_items,
            exclusions=exclusions,
            raw_text=text,
            extraction_metadata=extraction_metadata,
            source_filename=source_filename
        )
        
        # Add audit entry
        policy.add_audit_entry(
            action="policy_extracted",
            details={
                "clauses_count": len(clauses),
                "coverage_count": len(coverage_items),
                "exclusions_count": len(exclusions),
                "confidence": overall_confidence,
                "processing_time_ms": processing_time
            }
        )
        
        logger.info(
            f"Policy extraction complete: {len(clauses)} clauses, "
            f"{len(coverage_items)} coverage items, {len(exclusions)} exclusions"
        )
        
        return policy


# Singleton instance
_extractor: Optional[PolicyExtractor] = None


def get_policy_extractor() -> PolicyExtractor:
    """Get the policy extractor singleton."""
    global _extractor
    if _extractor is None:
        _extractor = PolicyExtractor()
    return _extractor