# app/storage/base.py
"""Base storage interface."""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, List, Dict, Any
from pathlib import Path
import json
import os
from datetime import datetime, date

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


class JSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for datetime and date objects."""
    
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, date):
            return obj.isoformat()
        return super().default(obj)


class BaseStore(ABC, Generic[T]):
    """Abstract base class for all storage implementations."""
    
    def __init__(self, data_dir: str, filename: str):
        self.data_dir = Path(data_dir)
        self.filepath = self.data_dir / filename
        self._ensure_directory()
        self._cache: Dict[str, T] = {}
        self._loaded = False
    
    def _ensure_directory(self):
        """Ensure data directory exists."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_data(self) -> Dict[str, Any]:
        """Load data from JSON file."""
        if not self.filepath.exists():
            return {}
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load {self.filepath}: {e}")
            return {}
    
    def _save_data(self, data: Dict[str, Any]):
        """Save data to JSON file."""
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, cls=JSONEncoder)
        except Exception as e:
            logger.error(f"Failed to save {self.filepath}: {e}")
            raise
    
    @abstractmethod
    def _serialize(self, entity: T) -> Dict[str, Any]:
        """Serialize entity to dict."""
        pass
    
    @abstractmethod
    def _deserialize(self, data: Dict[str, Any]) -> T:
        """Deserialize dict to entity."""
        pass
    
    @abstractmethod
    def _get_id(self, entity: T) -> str:
        """Get entity ID."""
        pass
    
    def _load_all(self) -> Dict[str, T]:
        """Load and deserialize all entities."""
        if not self._loaded:
            data = self._load_data()
            for key, value in data.items():
                try:
                    self._cache[key] = self._deserialize(value)
                except Exception as e:
                    logger.error(f"Failed to deserialize {key}: {e}")
            self._loaded = True
        return self._cache
    
    def save(self, entity: T) -> T:
        """Save an entity."""
        self._load_all()  # Ensure cache is loaded
        entity_id = self._get_id(entity)
        self._cache[entity_id] = entity
        
        # Serialize all and save
        data = {k: self._serialize(v) for k, v in self._cache.items()}
        self._save_data(data)
        
        logger.info(f"Saved entity: {entity_id}")
        return entity
    
    def get(self, entity_id: str) -> Optional[T]:
        """Get entity by ID."""
        self._load_all()
        return self._cache.get(entity_id)
    
    def get_all(self) -> List[T]:
        """Get all entities."""
        self._load_all()
        return list(self._cache.values())
    
    def delete(self, entity_id: str) -> bool:
        """Delete an entity."""
        self._load_all()
        if entity_id not in self._cache:
            return False
        
        del self._cache[entity_id]
        
        data = {k: self._serialize(v) for k, v in self._cache.items()}
        self._save_data(data)
        
        logger.info(f"Deleted entity: {entity_id}")
        return True
    
    def exists(self, entity_id: str) -> bool:
        """Check if entity exists."""
        self._load_all()
        return entity_id in self._cache
    
    def count(self) -> int:
        """Count total entities."""
        self._load_all()
        return len(self._cache)
    
    def query(self, filters: Dict[str, Any]) -> List[T]:
        """Query entities with filters (basic implementation)."""
        self._load_all()
        results = []
        
        for entity in self._cache.values():
            match = True
            entity_dict = self._serialize(entity)
            
            for key, value in filters.items():
                if key not in entity_dict or entity_dict[key] != value:
                    match = False
                    break
            
            if match:
                results.append(entity)
        
        return results