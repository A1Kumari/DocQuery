# app/models/enums.py
from enum import Enum

class PolicyType(str, Enum):
    HEALTH = "health"
    AUTO = "auto"
    HOME = "home"
    LIFE = "life"
    TRAVEL = "travel"
    
class ClaimType(str, Enum):
    MEDICAL = "medical"
    HOSPITALIZATION = "hospitalization"
    SURGERY = "surgery"
    MEDICATION = "medication"
    ACCIDENT = "accident"
    PROPERTY_DAMAGE = "property_damage"
    THEFT = "theft"
    LIABILITY = "liability"
    DEATH_BENEFIT = "death_benefit"
    
class ClaimStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    PENDING_INFO = "pending_info"
    APPROVED = "approved"
    PARTIALLY_APPROVED = "partially_approved"
    DENIED = "denied"
    FLAGGED_FRAUD = "flagged_fraud"
    CLOSED = "closed"

class ClauseType(str, Enum):
    COVERAGE = "coverage"
    EXCLUSION = "exclusion"
    CONDITION = "condition"
    LIMITATION = "limitation"
    DEFINITION = "definition"
    PROCEDURE = "procedure"

class FraudSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"