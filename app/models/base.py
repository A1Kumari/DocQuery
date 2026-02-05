# app/models/base.py
"""Base models for all entities."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid


def generate_id(prefix: str = "") -> str:
    """Generate a unique ID with optional prefix."""
    unique_part = uuid.uuid4().hex[:12]
    return f"{prefix}_{unique_part}" if prefix else unique_part


class TimestampMixin(BaseModel):
    """Mixin for timestamp fields."""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    def touch(self):
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()


class BaseEntity(TimestampMixin):
    """Base entity with common fields."""
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AuditLog(BaseModel):
    """Audit log entry."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    action: str
    actor: Optional[str] = None  # User or system
    details: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }