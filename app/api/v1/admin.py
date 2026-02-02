# app/api/v1/admin.py
from fastapi import APIRouter, HTTPException
from app.core.config import settings
from app.core.dependencies import get_neo4j_client
from app.services.store import list_files
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.get("/health")
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "llm_provider": settings.LLM_PROVIDER,
        "debug_mode": settings.DEBUG
    }

@router.get("/stats")
async def get_system_stats():
    """Get system statistics."""
    files = list_files()
    
    return {
        "total_documents": len(files),
        "total_chunks": sum(f.get("chunk_count", 0) for f in files),
        "llm_provider": settings.LLM_PROVIDER,
        # TODO: Add more stats
        "policies_count": 0,
        "claims_count": 0,
        "pending_validations": 0
    }

@router.get("/neo4j/status")
async def neo4j_status():
    """Check Neo4j connection status."""
    try:
        client = get_neo4j_client()
        # TODO: Implement connection test
        return {
            "connected": True,
            "uri": settings.NEO4J_URI
        }
    except Exception as e:
        return {
            "connected": False,
            "error": str(e)
        }