# app/core/dependencies.py
from typing import Generator, Optional
from functools import lru_cache

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# ===================
# Database Clients
# ===================

_neo4j_client = None
_pinecone_client = None

def get_neo4j_client():
    """Get Neo4j client instance."""
    global _neo4j_client
    if _neo4j_client is None:
        from app.database.neo4j_client import Neo4jClient
        _neo4j_client = Neo4jClient()
        logger.info("Neo4j client initialized")
    return _neo4j_client

def get_pinecone_client():
    """Get Pinecone client instance."""
    global _pinecone_client
    if _pinecone_client is None:
        from app.database.pinecone_client import PineconeClient
        _pinecone_client = PineconeClient()
        logger.info("Pinecone client initialized")
    return _pinecone_client

# ===================
# Service Instances
# ===================

_policy_extractor = None
_claim_validator = None
_fraud_detector = None

def get_policy_extractor():
    """Get policy extractor service."""
    global _policy_extractor
    if _policy_extractor is None:
        from app.services.policy_extractor import PolicyExtractor
        _policy_extractor = PolicyExtractor()
        logger.info("Policy extractor initialized")
    return _policy_extractor

def get_claim_validator():
    """Get claim validator agent."""
    global _claim_validator
    if _claim_validator is None:
        from app.services.claim_validator import ClaimValidatorAgent
        _claim_validator = ClaimValidatorAgent(
            neo4j_client=get_neo4j_client(),
            pinecone_client=get_pinecone_client()
        )
        logger.info("Claim validator initialized")
    return _claim_validator

def get_fraud_detector():
    """Get fraud detector service."""
    global _fraud_detector
    if _fraud_detector is None:
        from app.services.fraud_detector import FraudDetector
        _fraud_detector = FraudDetector()
        logger.info("Fraud detector initialized")
    return _fraud_detector

# ===================
# Cleanup
# ===================

async def cleanup_resources():
    """Cleanup all resources on shutdown."""
    global _neo4j_client, _pinecone_client
    
    if _neo4j_client:
        await _neo4j_client.close()
        _neo4j_client = None
        logger.info("Neo4j client closed")