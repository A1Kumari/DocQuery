# app/core/constants.py
"""Application constants and enums."""

from enum import Enum
from typing import List


# ===================
# Policy Constants
# ===================

class PolicyType(str, Enum):
    HEALTH = "health"
    AUTO = "auto"
    HOME = "home"
    LIFE = "life"
    TRAVEL = "travel"
    
    @classmethod
    def values(cls) -> List[str]:
        return [e.value for e in cls]


class ClauseType(str, Enum):
    COVERAGE = "coverage"
    EXCLUSION = "exclusion"
    CONDITION = "condition"
    LIMITATION = "limitation"
    DEFINITION = "definition"
    PROCEDURE = "procedure"
    
    @classmethod
    def values(cls) -> List[str]:
        return [e.value for e in cls]


class PolicyStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    SUSPENDED = "suspended"


# ===================
# Claim Constants
# ===================

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
    
    @classmethod
    def values(cls) -> List[str]:
        return [e.value for e in cls]


class ClaimStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    PENDING_DOCUMENTS = "pending_documents"
    PENDING_INFO = "pending_info"
    VALIDATING = "validating"
    APPROVED = "approved"
    PARTIALLY_APPROVED = "partially_approved"
    DENIED = "denied"
    FLAGGED_FRAUD = "flagged_fraud"
    INVESTIGATING = "investigating"
    CLOSED = "closed"
    CANCELLED = "cancelled"
    
    @classmethod
    def values(cls) -> List[str]:
        return [e.value for e in cls]
    
    @classmethod
    def terminal_statuses(cls) -> List[str]:
        """Statuses that cannot be changed."""
        return [cls.CLOSED.value, cls.CANCELLED.value]
    
    @classmethod
    def valid_transitions(cls) -> dict:
        """Valid status transitions."""
        return {
            cls.DRAFT: [cls.SUBMITTED, cls.CANCELLED],
            cls.SUBMITTED: [cls.UNDER_REVIEW, cls.PENDING_DOCUMENTS, cls.CANCELLED],
            cls.UNDER_REVIEW: [cls.VALIDATING, cls.PENDING_INFO, cls.PENDING_DOCUMENTS],
            cls.PENDING_DOCUMENTS: [cls.UNDER_REVIEW, cls.CANCELLED],
            cls.PENDING_INFO: [cls.UNDER_REVIEW, cls.CANCELLED],
            cls.VALIDATING: [cls.APPROVED, cls.PARTIALLY_APPROVED, cls.DENIED, cls.FLAGGED_FRAUD],
            cls.APPROVED: [cls.CLOSED],
            cls.PARTIALLY_APPROVED: [cls.CLOSED],
            cls.DENIED: [cls.CLOSED, cls.UNDER_REVIEW],  # Can appeal
            cls.FLAGGED_FRAUD: [cls.INVESTIGATING],
            cls.INVESTIGATING: [cls.APPROVED, cls.DENIED, cls.CLOSED],
        }


class FraudSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FraudIndicatorType(str, Enum):
    TIMING_ANOMALY = "timing_anomaly"
    AMOUNT_ANOMALY = "amount_anomaly"
    PATTERN_MATCH = "pattern_match"
    DUPLICATE_CLAIM = "duplicate_claim"
    INCONSISTENT_INFO = "inconsistent_info"
    FREQUENCY_ANOMALY = "frequency_anomaly"
    DOCUMENT_ISSUE = "document_issue"


# ===================
# Document Constants
# ===================

class DocumentType(str, Enum):
    POLICY = "policy"
    CLAIM_SUPPORT = "claim_support"
    MEDICAL_REPORT = "medical_report"
    RECEIPT = "receipt"
    POLICE_REPORT = "police_report"
    PHOTO = "photo"
    ID_PROOF = "id_proof"
    OTHER = "other"


# ===================
# Processing Constants
# ===================

ALLOWED_FILE_EXTENSIONS = [".pdf"]
MAX_FILE_SIZE_MB = 50
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 200

# Fraud thresholds
FRAUD_SCORE_LOW = 0.3
FRAUD_SCORE_MEDIUM = 0.5
FRAUD_SCORE_HIGH = 0.7
FRAUD_SCORE_CRITICAL = 0.85

# Validation thresholds
AUTO_APPROVE_CONFIDENCE = 0.9
MANUAL_REVIEW_CONFIDENCE = 0.7