# app/models/claim.py
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date
from app.models.enums import ClaimType, ClaimStatus, FraudSeverity

# ===================
# Supporting Models
# ===================

class ClaimDocument(BaseModel):
    """Document attached to a claim."""
    document_id: str
    document_type: str  # receipt, medical_report, police_report, photo
    filename: str
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    verified: bool = False

class FraudIndicator(BaseModel):
    """Individual fraud indicator."""
    indicator_id: str
    indicator_type: str
    severity: FraudSeverity
    description: str
    evidence: List[str] = Field(default_factory=list)
    score_contribution: float = 0.0

class ValidationStep(BaseModel):
    """Individual step in validation process."""
    step_name: str
    status: str  # passed, failed, warning, skipped
    details: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Optional[dict] = None

# ===================
# Main Claim Models
# ===================

class ClaimBase(BaseModel):
    """Base claim information."""
    policy_id: str
    claim_type: ClaimType
    incident_date: date
    incident_description: str
    claimed_amount: float
    incident_location: Optional[str] = None

class ClaimCreate(ClaimBase):
    """For submitting a new claim."""
    claimant_name: str
    claimant_contact: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "policy_id": "pol_123abc",
                "claim_type": "hospitalization",
                "incident_date": "2024-01-15",
                "incident_description": "Emergency appendectomy surgery due to acute appendicitis",
                "claimed_amount": 15000.00,
                "incident_location": "City General Hospital",
                "claimant_name": "John Doe",
                "claimant_contact": "john@example.com"
            }
        }

class Claim(ClaimBase):
    """Complete claim with all details."""
    claim_id: str
    claim_number: str
    claimant_name: str
    claimant_contact: Optional[str] = None
    
    # Status tracking
    status: ClaimStatus = ClaimStatus.SUBMITTED
    status_history: List[dict] = Field(default_factory=list)
    
    # Documents
    documents: List[ClaimDocument] = Field(default_factory=list)
    
    # Processing
    assigned_to: Optional[str] = None
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Validation result (populated after validation)
    validation_result: Optional["ClaimValidationResult"] = None

class ClaimValidationResult(BaseModel):
    """Result of claim validation process."""
    claim_id: str
    validation_id: str
    
    # Overall result
    is_valid: bool
    recommendation: str  # approve, deny, review, investigate
    confidence_score: float = Field(ge=0, le=1)
    
    # Coverage analysis
    coverage_applies: bool
    applicable_coverage: Optional[dict] = None
    coverage_limit: float = 0.0
    deductible: float = 0.0
    
    # Exclusion analysis
    exclusions_triggered: List[str] = Field(default_factory=list)
    exclusion_details: List[dict] = Field(default_factory=list)
    
    # Payout calculation
    claimed_amount: float
    approved_amount: float = 0.0
    recommended_payout: float = 0.0
    payout_breakdown: Optional[dict] = None
    
    # Fraud analysis
    fraud_flags: List[FraudIndicator] = Field(default_factory=list)
    fraud_risk_score: float = Field(ge=0, le=1, default=0.0)
    requires_investigation: bool = False
    
    # Validation steps (audit trail)
    validation_steps: List[ValidationStep] = Field(default_factory=list)
    relevant_clauses: List[str] = Field(default_factory=list)
    relevant_sources: List[dict] = Field(default_factory=list)
    
    # Reasoning
    reasoning_summary: str = ""
    detailed_reasoning: Optional[str] = None
    
    # Metadata
    validated_at: datetime = Field(default_factory=datetime.utcnow)
    processing_time_ms: float = 0.0
    model_used: str = ""

class ClaimSummary(BaseModel):
    """Brief claim summary for listings."""
    claim_id: str
    claim_number: str
    policy_id: str
    claim_type: ClaimType
    status: ClaimStatus
    claimed_amount: float
    incident_date: date
    submitted_at: datetime
    fraud_risk_score: Optional[float] = None

# ===================
# API Request/Response Models
# ===================

class ClaimSubmitResponse(BaseModel):
    """Response after claim submission."""
    success: bool
    claim_id: str
    claim_number: str
    message: str
    status: ClaimStatus

class ClaimValidateRequest(BaseModel):
    """Request to validate a claim."""
    claim_id: str
    include_fraud_check: bool = True
    include_similar_claims: bool = True
    
class ClaimValidateResponse(BaseModel):
    """Response from claim validation."""
    success: bool
    claim_id: str
    validation_result: ClaimValidationResult
    processing_time_ms: float

# Forward reference update
Claim.model_rebuild()