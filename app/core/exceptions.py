# app/core/exceptions.py
"""Custom exceptions for ClaimCheck application."""

from typing import Optional, Dict, Any


class ClaimCheckException(Exception):
    """Base exception for all ClaimCheck errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


# ===================
# Policy Exceptions
# ===================

class PolicyException(ClaimCheckException):
    """Base exception for policy-related errors."""
    pass


class PolicyNotFoundError(PolicyException):
    """Policy not found in storage."""
    
    def __init__(self, policy_id: str):
        super().__init__(
            message=f"Policy not found: {policy_id}",
            error_code="POLICY_NOT_FOUND",
            details={"policy_id": policy_id}
        )


class PolicyExtractionError(PolicyException):
    """Error during policy extraction."""
    
    def __init__(self, message: str, policy_id: Optional[str] = None):
        super().__init__(
            message=f"Policy extraction failed: {message}",
            error_code="POLICY_EXTRACTION_ERROR",
            details={"policy_id": policy_id} if policy_id else {}
        )


class PolicyValidationError(PolicyException):
    """Policy data validation error."""
    
    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(
            message=f"Policy validation failed: {message}",
            error_code="POLICY_VALIDATION_ERROR",
            details={"field": field} if field else {}
        )


# ===================
# Claim Exceptions
# ===================

class ClaimException(ClaimCheckException):
    """Base exception for claim-related errors."""
    pass


class ClaimNotFoundError(ClaimException):
    """Claim not found in storage."""
    
    def __init__(self, claim_id: str):
        super().__init__(
            message=f"Claim not found: {claim_id}",
            error_code="CLAIM_NOT_FOUND",
            details={"claim_id": claim_id}
        )


class ClaimValidationError(ClaimException):
    """Error during claim validation."""
    
    def __init__(self, message: str, claim_id: Optional[str] = None):
        super().__init__(
            message=f"Claim validation failed: {message}",
            error_code="CLAIM_VALIDATION_ERROR",
            details={"claim_id": claim_id} if claim_id else {}
        )


class InvalidClaimStatusTransition(ClaimException):
    """Invalid claim status transition."""
    
    def __init__(self, current_status: str, new_status: str):
        super().__init__(
            message=f"Cannot transition from {current_status} to {new_status}",
            error_code="INVALID_STATUS_TRANSITION",
            details={"current_status": current_status, "new_status": new_status}
        )


# ===================
# Document Exceptions
# ===================

class DocumentException(ClaimCheckException):
    """Base exception for document-related errors."""
    pass


class DocumentNotFoundError(DocumentException):
    """Document not found."""
    
    def __init__(self, document_id: str):
        super().__init__(
            message=f"Document not found: {document_id}",
            error_code="DOCUMENT_NOT_FOUND",
            details={"document_id": document_id}
        )


class DocumentProcessingError(DocumentException):
    """Error during document processing."""
    
    def __init__(self, message: str, filename: Optional[str] = None):
        super().__init__(
            message=f"Document processing failed: {message}",
            error_code="DOCUMENT_PROCESSING_ERROR",
            details={"filename": filename} if filename else {}
        )


class UnsupportedFileTypeError(DocumentException):
    """Unsupported file type."""
    
    def __init__(self, filename: str, allowed_types: list):
        super().__init__(
            message=f"Unsupported file type: {filename}",
            error_code="UNSUPPORTED_FILE_TYPE",
            details={"filename": filename, "allowed_types": allowed_types}
        )


# ===================
# AI/LLM Exceptions
# ===================

class AIException(ClaimCheckException):
    """Base exception for AI-related errors."""
    pass


class LLMConnectionError(AIException):
    """Cannot connect to LLM provider."""
    
    def __init__(self, provider: str, message: str):
        super().__init__(
            message=f"LLM connection failed ({provider}): {message}",
            error_code="LLM_CONNECTION_ERROR",
            details={"provider": provider}
        )


class ExtractionError(AIException):
    """Error during AI extraction."""
    
    def __init__(self, message: str):
        super().__init__(
            message=f"Extraction failed: {message}",
            error_code="EXTRACTION_ERROR"
        )


# ===================
# Storage Exceptions
# ===================

class StorageException(ClaimCheckException):
    """Base exception for storage-related errors."""
    pass


class Neo4jConnectionError(StorageException):
    """Cannot connect to Neo4j."""
    
    def __init__(self, message: str):
        super().__init__(
            message=f"Neo4j connection failed: {message}",
            error_code="NEO4J_CONNECTION_ERROR"
        )


class PineconeConnectionError(StorageException):
    """Cannot connect to Pinecone."""
    
    def __init__(self, message: str):
        super().__init__(
            message=f"Pinecone connection failed: {message}",
            error_code="PINECONE_CONNECTION_ERROR"
        )