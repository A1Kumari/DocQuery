# app/storage/policy_store.py
"""JSON-based storage for policy data."""

import json
import os
from pathlib import Path
from typing import Optional, List, Tuple
from datetime import date, datetime

from app.models.policy import PolicyDocument, PolicyHolder, Clause, CoverageLimit, Exclusion, PolicySummary
from app.models.enums import PolicyType, ClauseType
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class JSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for dates and enums."""
    
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, date):
            return obj.isoformat()
        if hasattr(obj, 'value'):  # Enum
            return obj.value
        return super().default(obj)


class PolicyStore:
    """
    JSON file-based storage for policies.
    
    Stores all policies in a single JSON file for simplicity.
    For production, replace with a proper database.
    """
    
    def __init__(self):
        # Ensure data directory exists
        self.data_dir = Path(settings.DATA_DIR) / "policies"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.filepath = self.data_dir / "policies.json"
        
        # In-memory cache
        self._cache: dict[str, PolicyDocument] = {}
        self._loaded = False
    
    def _load_all(self) -> dict[str, PolicyDocument]:
        """Load all policies from JSON file into cache."""
        if self._loaded:
            return self._cache
        
        if not self.filepath.exists():
            self._cache = {}
            self._loaded = True
            return self._cache
        
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self._cache = {}
            for policy_id, policy_data in data.items():
                try:
                    policy = self._deserialize(policy_data)
                    self._cache[policy_id] = policy
                except Exception as e:
                    logger.error(f"Failed to deserialize policy {policy_id}: {e}")
            
            self._loaded = True
            logger.info(f"Loaded {len(self._cache)} policies from storage")
            
        except Exception as e:
            logger.error(f"Failed to load policies: {e}")
            self._cache = {}
            self._loaded = True
        
        return self._cache
    
    def _save_all(self):
        """Save all policies from cache to JSON file."""
        try:
            data = {
                policy_id: self._serialize(policy)
                for policy_id, policy in self._cache.items()
            }
            
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, cls=JSONEncoder)
            
            logger.debug(f"Saved {len(self._cache)} policies to storage")
            
        except Exception as e:
            logger.error(f"Failed to save policies: {e}")
            raise
    
    def _serialize(self, policy: PolicyDocument) -> dict:
        """Convert PolicyDocument to dict for JSON storage."""
        return policy.model_dump(mode='json')
    
    def _deserialize(self, data: dict) -> PolicyDocument:
        """Convert dict from JSON to PolicyDocument."""
        
        # Convert date strings to date objects
        if isinstance(data.get('effective_date'), str):
            data['effective_date'] = date.fromisoformat(data['effective_date'])
        if isinstance(data.get('expiration_date'), str):
            data['expiration_date'] = date.fromisoformat(data['expiration_date'])
        
        # Convert holder
        if isinstance(data.get('holder'), dict):
            holder_data = data['holder']
            if isinstance(holder_data.get('date_of_birth'), str):
                holder_data['date_of_birth'] = date.fromisoformat(holder_data['date_of_birth'])
            data['holder'] = PolicyHolder(**holder_data)
        
        # Convert clauses
        if 'clauses' in data and data['clauses']:
            data['clauses'] = [
                Clause(**c) if isinstance(c, dict) else c
                for c in data['clauses']
            ]
        
        # Convert coverage limits
        if 'coverage_limits' in data and data['coverage_limits']:
            data['coverage_limits'] = [
                CoverageLimit(**c) if isinstance(c, dict) else c
                for c in data['coverage_limits']
            ]
        
        # Convert exclusions
        if 'exclusions' in data and data['exclusions']:
            data['exclusions'] = [
                Exclusion(**e) if isinstance(e, dict) else e
                for e in data['exclusions']
            ]
        
        # Convert timestamps
        if isinstance(data.get('created_at'), str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if isinstance(data.get('updated_at'), str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        
        return PolicyDocument(**data)
    
    # ===================
    # CRUD Operations
    # ===================
    
    def save(self, policy: PolicyDocument) -> PolicyDocument:
        """Save or update a policy."""
        self._load_all()
        
        # Update timestamp
        policy.updated_at = datetime.utcnow()
        
        # Save to cache
        self._cache[policy.policy_id] = policy
        
        # Persist to file
        self._save_all()
        
        logger.info(f"Saved policy: {policy.policy_id}")
        return policy
    
    def get(self, policy_id: str) -> Optional[PolicyDocument]:
        """Get policy by ID."""
        self._load_all()
        return self._cache.get(policy_id)
    
    def get_by_number(self, policy_number: str) -> Optional[PolicyDocument]:
        """Get policy by policy number."""
        self._load_all()
        for policy in self._cache.values():
            if policy.policy_number == policy_number:
                return policy
        return None
    
    def get_all(self) -> List[PolicyDocument]:
        """Get all policies."""
        self._load_all()
        return list(self._cache.values())
    
    def delete(self, policy_id: str) -> bool:
        """Delete a policy by ID."""
        self._load_all()
        
        if policy_id not in self._cache:
            return False
        
        del self._cache[policy_id]
        self._save_all()
        
        logger.info(f"Deleted policy: {policy_id}")
        return True
    
    def exists(self, policy_id: str) -> bool:
        """Check if policy exists."""
        self._load_all()
        return policy_id in self._cache
    
    def count(self) -> int:
        """Get total policy count."""
        self._load_all()
        return len(self._cache)
    
    # ===================
    # Query Methods
    # ===================
    
    def search(
        self,
        query: Optional[str] = None,
        policy_type: Optional[PolicyType] = None,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 10
    ) -> Tuple[List[PolicyDocument], int]:
        """
        Search policies with filters.
        
        Returns:
            Tuple of (policies, total_count)
        """
        self._load_all()
        
        results = list(self._cache.values())
        
        # Filter by active status
        if active_only:
            today = date.today()
            results = [
                p for p in results
                if p.effective_date <= today <= p.expiration_date
            ]
        
        # Filter by policy type
        if policy_type:
            results = [
                p for p in results
                if p.policy_type == policy_type or p.policy_type.value == policy_type
            ]
        
        # Search by query (policy number or holder name)
        if query:
            query_lower = query.lower()
            results = [
                p for p in results
                if query_lower in p.policy_number.lower() or
                   query_lower in p.holder.name.lower()
            ]
        
        # Get total before pagination
        total = len(results)
        
        # Sort by created_at descending (newest first)
        results.sort(key=lambda p: p.created_at, reverse=True)
        
        # Paginate
        results = results[skip:skip + limit]
        
        return results, total
    
    def get_expiring_soon(self, days: int = 30) -> List[PolicyDocument]:
        """Get policies expiring within specified days."""
        self._load_all()
        today = date.today()
        
        return [
            p for p in self._cache.values()
            if p.is_active and 0 < p.days_until_expiry <= days
        ]
    
    def get_by_holder(self, holder_name: str) -> List[PolicyDocument]:
        """Get all policies for a holder."""
        self._load_all()
        name_lower = holder_name.lower()
        
        return [
            p for p in self._cache.values()
            if name_lower in p.holder.name.lower()
        ]
    
    # ===================
    # Statistics
    # ===================
    
    def get_statistics(self) -> dict:
        """Get policy statistics for dashboard."""
        self._load_all()
        
        all_policies = list(self._cache.values())
        
        if not all_policies:
            return {
                "total": 0,
                "active": 0,
                "expired": 0,
                "by_type": {},
                "expiring_soon": 0
            }
        
        today = date.today()
        active = [p for p in all_policies if p.is_active]
        expired = [p for p in all_policies if p.expiration_date < today]
        expiring_soon = len(self.get_expiring_soon(30))
        
        # Count by type
        by_type = {}
        for p in all_policies:
            type_key = p.policy_type.value if hasattr(p.policy_type, 'value') else p.policy_type
            by_type[type_key] = by_type.get(type_key, 0) + 1
        
        return {
            "total": len(all_policies),
            "active": len(active),
            "expired": len(expired),
            "by_type": by_type,
            "expiring_soon": expiring_soon
        }


# ===================
# Singleton Instance
# ===================

_policy_store: Optional[PolicyStore] = None


def get_policy_store() -> PolicyStore:
    """Get the policy store singleton."""
    global _policy_store
    if _policy_store is None:
        _policy_store = PolicyStore()
    return _policy_store