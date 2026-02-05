# app/storage/claim_store.py
"""Claim storage implementation."""

from typing import Dict, Any, Optional, List
from datetime import date, datetime

from app.storage.base import BaseStore
from app.models.claim import (
    Claim, Claimant, IncidentDetails, ClaimDocument,
    ClaimValidationResult, FraudAnalysis, FraudIndicator,
    ValidationStep, PayoutCalculation, StatusChange
)
from app.core.constants import ClaimType, ClaimStatus, FraudSeverity
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class ClaimStore(BaseStore[Claim]):
    """Storage for claim entities."""
    
    def __init__(self):
        super().__init__(
            data_dir=f"{settings.DATA_DIR}/claims",
            filename="claims.json"
        )
    
    def _get_id(self, entity: Claim) -> str:
        return entity.claim_id
    
    def _serialize(self, entity: Claim) -> Dict[str, Any]:
        """Serialize Claim to dict."""
        return entity.model_dump(mode='json')
    
    def _deserialize(self, data: Dict[str, Any]) -> Claim:
        """Deserialize dict to Claim."""
        # Convert nested objects
        if isinstance(data.get('claimant'), dict):
            data['claimant'] = Claimant(**data['claimant'])
        
        if isinstance(data.get('incident'), dict):
            incident_data = data['incident']
            if isinstance(incident_data.get('date'), str):
                incident_data['date'] = date.fromisoformat(incident_data['date'])
            data['incident'] = IncidentDetails(**incident_data)
        
        # Convert documents
        if 'documents' in data:
            docs = []
            for d in data['documents']:
                if isinstance(d, dict):
                    if isinstance(d.get('uploaded_at'), str):
                        d['uploaded_at'] = datetime.fromisoformat(d['uploaded_at'])
                    docs.append(ClaimDocument(**d))
                else:
                    docs.append(d)
            data['documents'] = docs
        
        # Convert status history
        if 'status_history' in data:
            history = []
            for h in data['status_history']:
                if isinstance(h, dict):
                    if isinstance(h.get('changed_at'), str):
                        h['changed_at'] = datetime.fromisoformat(h['changed_at'])
                    history.append(StatusChange(**h))
                else:
                    history.append(h)
            data['status_history'] = history
        
        # Convert validation result (complex nested structure)
        if data.get('validation_result') and isinstance(data['validation_result'], dict):
            val_data = data['validation_result']
            
            # Convert fraud analysis
            if val_data.get('fraud_analysis') and isinstance(val_data['fraud_analysis'], dict):
                fraud_data = val_data['fraud_analysis']
                if 'indicators' in fraud_data:
                    fraud_data['indicators'] = [
                        FraudIndicator(**i) if isinstance(i, dict) else i
                        for i in fraud_data['indicators']
                    ]
                val_data['fraud_analysis'] = FraudAnalysis(**fraud_data)
            
            # Convert payout calculation
            if val_data.get('payout_calculation') and isinstance(val_data['payout_calculation'], dict):
                val_data['payout_calculation'] = PayoutCalculation(**val_data['payout_calculation'])
            
            # Convert validation steps
            if 'validation_steps' in val_data:
                val_data['validation_steps'] = [
                    ValidationStep(**s) if isinstance(s, dict) else s
                    for s in val_data['validation_steps']
                ]
            
            data['validation_result'] = ClaimValidationResult(**val_data)
        
        # Convert timestamps
        for ts_field in ['created_at', 'updated_at', 'submitted_at', 'validated_at', 'decided_at', 'paid_at']:
            if isinstance(data.get(ts_field), str):
                data[ts_field] = datetime.fromisoformat(data[ts_field])
        
        return Claim(**data)
    
    # Custom query methods
    def get_by_claim_number(self, claim_number: str) -> Optional[Claim]:
        """Find claim by claim number."""
        for claim in self.get_all():
            if claim.claim_number == claim_number:
                return claim
        return None
    
    def get_by_policy(self, policy_id: str) -> List[Claim]:
        """Get all claims for a policy."""
        return [c for c in self.get_all() if c.policy_id == policy_id]
    
    def get_by_status(self, status: ClaimStatus) -> List[Claim]:
        """Get claims by status."""
        return [c for c in self.get_all() if c.status == status]
    
    def get_pending_claims(self) -> List[Claim]:
        """Get all pending claims."""
        return [c for c in self.get_all() if c.is_pending]
    
    def get_flagged_fraud(self) -> List[Claim]:
        """Get claims flagged for fraud."""
        return [
            c for c in self.get_all() 
            if c.status == ClaimStatus.FLAGGED_FRAUD or 
               (c.validation_result and 
                c.validation_result.fraud_analysis and 
                c.validation_result.fraud_analysis.requires_investigation)
        ]
    
    def get_high_value_claims(self, threshold: float = 10000) -> List[Claim]:
        """Get claims above a certain amount."""
        return [c for c in self.get_all() if c.claimed_amount >= threshold]
    
    def get_recent(self, days: int = 7) -> List[Claim]:
        """Get claims from the last N days."""
        cutoff = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff = cutoff.replace(day=cutoff.day - days)
        return [
            c for c in self.get_all() 
            if c.created_at >= cutoff
        ]
    
    def search(
        self,
        policy_id: str = None,
        status: ClaimStatus = None,
        claim_type: ClaimType = None,
        from_date: date = None,
        to_date: date = None,
        min_amount: float = None,
        max_amount: float = None,
        skip: int = 0,
        limit: int = 10
    ) -> tuple[List[Claim], int]:
        """Search claims with multiple filters."""
        results = self.get_all()
        
        if policy_id:
            results = [c for c in results if c.policy_id == policy_id]
        
        if status:
            results = [c for c in results if c.status == status]
        
        if claim_type:
            results = [c for c in results if c.claim_type == claim_type]
        
        if from_date:
            results = [c for c in results if c.incident.date >= from_date]
        
        if to_date:
            results = [c for c in results if c.incident.date <= to_date]
        
        if min_amount:
            results = [c for c in results if c.claimed_amount >= min_amount]
        
        if max_amount:
            results = [c for c in results if c.claimed_amount <= max_amount]
        
        total = len(results)
        
        # Sort by created_at descending
        results.sort(key=lambda c: c.created_at, reverse=True)
        
        # Paginate
        results = results[skip:skip + limit]
        
        return results, total
    
    # Statistics
    def get_statistics(self) -> Dict[str, Any]:
        """Get claim statistics."""
        all_claims = self.get_all()
        
        if not all_claims:
            return {
                "total": 0,
                "by_status": {},
                "by_type": {},
                "total_claimed": 0,
                "total_approved": 0,
                "average_claim": 0,
                "approval_rate": 0
            }
        
        by_status = {}
        by_type = {}
        total_claimed = 0
        total_approved = 0
        approved_count = 0
        decided_count = 0
        
        for claim in all_claims:
            # By status
            status_key = claim.status.value
            by_status[status_key] = by_status.get(status_key, 0) + 1
            
            # By type
            type_key = claim.claim_type.value
            by_type[type_key] = by_type.get(type_key, 0) + 1
            
            # Financials
            # app/storage/claim_store.py (continued)

    def get_statistics(self) -> Dict[str, Any]:
        """Get claim statistics."""
        all_claims = self.get_all()
        
        if not all_claims:
            return {
                "total": 0,
                "by_status": {},
                "by_type": {},
                "total_claimed": 0,
                "total_approved": 0,
                "total_denied": 0,
                "average_claim": 0,
                "approval_rate": 0,
                "average_processing_days": 0,
                "fraud_flagged": 0
            }
        
        by_status = {}
        by_type = {}
        total_claimed = 0
        total_approved = 0
        total_denied = 0
        approved_count = 0
        denied_count = 0
        fraud_flagged = 0
        processing_days = []
        
        for claim in all_claims:
            # By status
            status_key = claim.status.value
            by_status[status_key] = by_status.get(status_key, 0) + 1
            
            # By type
            type_key = claim.claim_type.value
            by_type[type_key] = by_type.get(type_key, 0) + 1
            
            # Financials
            total_claimed += claim.claimed_amount
            
            if claim.status == ClaimStatus.APPROVED:
                approved_count += 1
                total_approved += claim.approved_amount or claim.claimed_amount
            elif claim.status == ClaimStatus.PARTIALLY_APPROVED:
                approved_count += 1
                total_approved += claim.approved_amount or 0
            elif claim.status == ClaimStatus.DENIED:
                denied_count += 1
                total_denied += claim.claimed_amount
            
            # Fraud
            if claim.status == ClaimStatus.FLAGGED_FRAUD:
                fraud_flagged += 1
            
            # Processing time
            if claim.submitted_at and claim.decided_at:
                days = (claim.decided_at - claim.submitted_at).days
                processing_days.append(days)
        
        decided_count = approved_count + denied_count
        
        return {
            "total": len(all_claims),
            "by_status": by_status,
            "by_type": by_type,
            "total_claimed": round(total_claimed, 2),
            "total_approved": round(total_approved, 2),
            "total_denied": round(total_denied, 2),
            "average_claim": round(total_claimed / len(all_claims), 2),
            "approval_rate": round((approved_count / decided_count * 100), 2) if decided_count > 0 else 0,
            "average_processing_days": round(sum(processing_days) / len(processing_days), 1) if processing_days else 0,
            "fraud_flagged": fraud_flagged,
            "pending_count": len([c for c in all_claims if c.is_pending])
        }


# Singleton instance
_claim_store: Optional[ClaimStore] = None


def get_claim_store() -> ClaimStore:
    """Get the claim store singleton."""
    global _claim_store
    if _claim_store is None:
        _claim_store = ClaimStore()
    return _claim_store