# app/api/v1/policies.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel
from datetime import date, datetime

router = APIRouter()

# ===================
# Response Models
# ===================

class PolicyHolder(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None

class PolicySummary(BaseModel):
    policy_id: str
    policy_number: str
    policy_type: str
    holder_name: str
    effective_date: date
    expiration_date: date
    is_active: bool
    total_clauses: int = 0
    total_exclusions: int = 0
    created_at: datetime

class PolicyListResponse(BaseModel):
    total: int
    skip: int
    limit: int
    policies: List[PolicySummary]

class PolicyUploadResponse(BaseModel):
    success: bool
    policy_id: str
    policy_number: str
    message: str
    extraction_summary: dict
    processing_time_ms: float

# ===================
# Endpoints
# ===================

@router.post("/upload", response_model=PolicyUploadResponse)
async def upload_policy(
    file: UploadFile = File(...),
    policy_type: str = Query("health", description="Type: health, auto, home, life, travel"),
    policy_number: str = Query(..., description="Policy number"),
    holder_name: str = Query(..., description="Policy holder name"),
    holder_email: Optional[str] = Query(None, description="Holder email"),
    effective_date: date = Query(..., description="Policy start date"),
    expiration_date: date = Query(..., description="Policy end date"),
):
    """
    Upload an insurance policy document.
    Extracts clauses, coverage limits, and exclusions automatically.
    """
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # TODO: Implement actual policy extraction
    import uuid
    import time
    
    start_time = time.time()
    policy_id = f"pol_{uuid.uuid4().hex[:8]}"
    
    # Mock response for now
    return PolicyUploadResponse(
        success=True,
        policy_id=policy_id,
        policy_number=policy_number,
        message="Policy uploaded successfully. Extraction in progress.",
        extraction_summary={
            "clauses_extracted": 0,
            "exclusions_found": 0,
            "coverage_items": 0,
            "confidence_score": 0.0,
            "status": "pending"
        },
        processing_time_ms=round((time.time() - start_time) * 1000, 2)
    )

@router.get("/", response_model=PolicyListResponse)
async def list_policies(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    policy_type: Optional[str] = None,
    active_only: bool = Query(True, description="Only show active policies"),
    search: Optional[str] = Query(None, description="Search by policy number or holder name")
):
    """List all policies with optional filtering."""
    # TODO: Implement actual database query
    return PolicyListResponse(
        total=0,
        skip=skip,
        limit=limit,
        policies=[]
    )

@router.get("/{policy_id}")
async def get_policy(policy_id: str):
    """Get complete policy details including extracted information."""
    # TODO: Implement actual database lookup
    raise HTTPException(status_code=404, detail=f"Policy {policy_id} not found")

@router.get("/{policy_id}/summary")
async def get_policy_summary(policy_id: str):
    """Get a brief policy summary."""
    # TODO: Implement actual lookup
    raise HTTPException(status_code=404, detail=f"Policy {policy_id} not found")

@router.get("/{policy_id}/graph")
async def get_policy_graph(policy_id: str):
    """Get policy graph data for visualization (Neo4j)."""
    # TODO: Implement Neo4j query
    return {
        "policy_id": policy_id,
        "message": "Graph visualization - Coming soon (requires Neo4j)",
        "nodes": [],
        "edges": [],
        "statistics": {
            "total_nodes": 0,
            "total_edges": 0
        }
    }

@router.get("/{policy_id}/clauses")
async def get_policy_clauses(
    policy_id: str,
    clause_type: Optional[str] = Query(None, description="Filter: coverage, exclusion, condition, limitation")
):
    """Get extracted clauses from a policy."""
    # TODO: Implement actual lookup
    return {
        "policy_id": policy_id,
        "total": 0,
        "clauses": []
    }

@router.get("/{policy_id}/exclusions")
async def get_policy_exclusions(policy_id: str):
    """Get all exclusions from a policy."""
    # TODO: Implement actual lookup
    return {
        "policy_id": policy_id,
        "total": 0,
        "exclusions": []
    }

@router.get("/{policy_id}/coverage")
async def get_policy_coverage(policy_id: str):
    """Get coverage limits and details."""
    # TODO: Implement actual lookup
    return {
        "policy_id": policy_id,
        "total_coverage_amount": 0.0,
        "currency": "USD",
        "coverage_items": []
    }

@router.delete("/{policy_id}")
async def delete_policy(policy_id: str):
    """Delete a policy and its associated data."""
    # TODO: Implement actual deletion
    return {
        "success": True,
        "message": f"Policy {policy_id} deleted"
    }