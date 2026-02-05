# app/models/policy.py
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from app.models.enums import PolicyType, ClauseType

# ===================
# Sub-Models
# ===================

def generate_id(prefix: str = "") -> str:
    """Generate unique ID with prefix."""
    unique = uuid.uuid4().hex[:12]
    return f"{prefix}_{unique}" if prefix else unique

class Clause(BaseModel):
    """Individual clause extracted from policy."""
    clause_id: str = Field(..., description="Unique identifier for this clause")
    clause_type: ClauseType
    title: str
    description: str
    section_reference: Optional[str] = None
    page_number: Optional[int] = None
    conditions: List[str] = Field(default_factory=list)
    
    class Config:
        json_schema_extra = {
            "example": {
                "clause_id": "CL-001",
                "clause_type": "coverage",
                "title": "Hospitalization Coverage",
                "description": "Coverage for in-patient hospital stays...",
                "section_reference": "Section 4.2",
                "page_number": 12,
                "conditions": ["Must be medically necessary", "Pre-authorization required for elective procedures"]
            }
        }

class CoverageLimit(BaseModel):
    """Coverage limit details."""
    coverage_id: str
    coverage_type: str
    description: str
    limit_amount: float
    deductible: float = 0.0
    copay_percentage: Optional[float] = None
    currency: str = "USD"
    per_incident: bool = True
    annual_aggregate: Optional[float] = None
    waiting_period_days: int = 0
    
    class Config:
        json_schema_extra = {
            "example": {
                "coverage_id": "COV-001",
                "coverage_type": "hospitalization",
                "description": "In-patient hospital room and board",
                "limit_amount": 50000.0,
                "deductible": 500.0,
                "copay_percentage": 20.0,
                "currency": "USD",
                "per_incident": True,
                "annual_aggregate": 100000.0,
                "waiting_period_days": 30
            }
        }

class Exclusion(BaseModel):
    """Policy exclusion details."""
    exclusion_id: str
    category: str
    description: str
    keywords: List[str] = Field(default_factory=list)
    exceptions: List[str] = Field(default_factory=list, description="Cases where exclusion doesn't apply")
    
    class Config:
        json_schema_extra = {
            "example": {
                "exclusion_id": "EX-001",
                "category": "pre-existing conditions",
                "description": "Conditions diagnosed within 24 months before policy start",
                "keywords": ["pre-existing", "prior condition", "previous diagnosis"],
                "exceptions": ["Conditions disclosed during application and accepted"]
            }
        }

class PolicyHolder(BaseModel):
    """Policy holder information."""
    name: str
    policy_holder_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    date_of_birth: Optional[date] = None

# ===================
# Main Policy Model
# ===================

class PolicyBase(BaseModel):
    """Base policy information."""
    policy_number: str
    policy_type: PolicyType
    holder: PolicyHolder
    effective_date: date
    expiration_date: date
    premium_amount: Optional[float] = None
    premium_frequency: Optional[str] = None  # monthly, quarterly, annual

class PolicyCreate(PolicyBase):
    """For creating a new policy (upload)."""
    pass

class PolicyDocument(PolicyBase):
    """Complete policy with all extracted information."""
    policy_id: str = Field(default_factory=lambda: generate_id("pol"))  # THIS LINE
    
    
    # Extracted structured data
    clauses: List[Clause] = Field(default_factory=list)
    coverage_limits: List[CoverageLimit] = Field(default_factory=list)
    exclusions: List[Exclusion] = Field(default_factory=list)
    
    # Raw content
    raw_text: str = ""
    total_pages: int = 0
    
    # Vector store references
    chunk_ids: List[str] = Field(default_factory=list)
    
    # Processing metadata
    extraction_confidence: float = 0.0
    processing_status: str = "pending"  # pending, processing, completed, failed
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "policy_id": "pol_123abc",
                "policy_number": "POL-2024-001234",
                "policy_type": "health",
                "holder": {
                    "name": "John Doe",
                    "email": "john@example.com"
                },
                "effective_date": "2024-01-01",
                "expiration_date": "2025-01-01",
                "clauses": [],
                "coverage_limits": [],
                "exclusions": [],
                "extraction_confidence": 0.92
            }
        }

class PolicySummary(BaseModel):
    """Brief policy summary for listings."""
    policy_id: str
    policy_number: str
    policy_type: PolicyType
    holder_name: str
    effective_date: date
    expiration_date: date
    is_active: bool
    total_clauses: int
    total_exclusions: int
    created_at: datetime

# ===================
# API Response Models
# ===================

class PolicyUploadResponse(BaseModel):
    """Response after policy upload."""
    success: bool
    policy_id: str
    policy_number: str
    message: str
    extraction_summary: dict
    processing_time_ms: float

class PolicyGraphResponse(BaseModel):
    """Neo4j graph data for visualization."""
    policy_id: str
    nodes: List[dict]
    edges: List[dict]
    statistics: dict

