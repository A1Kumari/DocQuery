# app/routers/claims.py
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from app.models.claim import Claim, ClaimValidationResult, ClaimStatus
from app.agents.claim_validator import ClaimValidatorAgent
from app.database.neo4j_client import Neo4jClient
from app.database.pinecone_client import PineconeClient

router = APIRouter(prefix="/claims", tags=["claims"])

# Dependency injection
async def get_validator():
    neo4j = Neo4jClient()
    pinecone = PineconeClient()
    validator = ClaimValidatorAgent(neo4j, pinecone)
    try:
        yield validator
    finally:
        await neo4j.close()

@router.post("/", response_model=Claim)
async def submit_claim(claim: Claim):
    """Submit a new claim."""
    # Store claim in database
    # For now, just return with ID
    return claim

@router.post("/{claim_id}/validate", response_model=ClaimValidationResult)
async def validate_claim(
    claim_id: str,
    policy_id: str,
    validator: ClaimValidatorAgent = Depends(get_validator)
):
    """Validate a claim against its policy."""
    
    # Fetch claim from database (simplified)
    claim = Claim(
        claim_id=claim_id,
        policy_id=policy_id,
        claim_type="medical",
        incident_date="2024-01-15",
        submission_date="2024-01-20",
        description="Hospital admission for emergency surgery",
        claimed_amount=15000.00
    )
    
    result = await validator.validate_claim(claim, policy_id)
    return result

@router.get("/{claim_id}/status")
async def get_claim_status(claim_id: str):
    """Get current claim status."""
    return {"claim_id": claim_id, "status": ClaimStatus.UNDER_REVIEW}