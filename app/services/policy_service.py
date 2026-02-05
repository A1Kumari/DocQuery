# app/services/policy_service.py
"""Policy business logic service."""

from typing import Optional, List, Tuple
from datetime import date
import time

from fastapi import UploadFile

from app.models.policy import Policy, PolicyHolder, PolicySummary
from app.core.constants import PolicyType, PolicyStatus
from app.storage.policy_store import get_policy_store
from app.ai.extractor import get_policy_extractor
from app.ai.embeddings import get_embedding_service
from app.utils.pdf import extract_text_from_pdf
from app.core.logging import get_logger
from app.core.exceptions import (
    PolicyNotFoundError, PolicyValidationError, DocumentProcessingError
)

logger = get_logger(__name__)


class PolicyService:
    """Service for policy operations."""
    
    def __init__(self):
        self.store = get_policy_store()
        self.extractor = get_policy_extractor()
        self.embeddings = get_embedding_service()
    
    async def create_policy_from_document(
        self,
        file: UploadFile,
        policy_number: str,
        policy_type: PolicyType,
        holder_name: str,
        holder_email: Optional[str],
        effective_date: date,
        expiration_date: date
    ) -> Policy:
        """
        Create a new policy from an uploaded document.
        
        1. Extract text from PDF
        2. Use AI to extract structured information
        3. Store vectors in Pinecone
        4. Save policy to storage
        """
        logger.info(f"Creating policy from document: {file.filename}")
        start_time = time.time()
        
        # Validate dates
        if expiration_date <= effective_date:
            raise PolicyValidationError(
                "Expiration date must be after effective date",
                field="expiration_date"
            )
        
        # Extract text from PDF
        try:
            text, page_count = await extract_text_from_pdf(file)
        except Exception as e:
            raise DocumentProcessingError(str(e), file.filename)
        
        if not text or len(text.strip()) < 100:
            raise DocumentProcessingError(
                "Could not extract sufficient text from document",
                file.filename
            )
        
        # Create holder
        holder = PolicyHolder(
            name=holder_name,
            email=holder_email
        )
        
        # Extract structured information using AI
        policy = await self.extractor.extract_full_policy(
            text=text,
            policy_number=policy_number,
            policy_type=policy_type,
            holder=holder,
            effective_date=effective_date,
            expiration_date=expiration_date,
            source_filename=file.filename
        )
        
        # Update extraction metadata with page count
        if policy.extraction_metadata:
            policy.extraction_metadata.total_pages = page_count
        
        # Store document chunks in vector store
        try:
            chunk_ids = await self._store_policy_vectors(policy)
            policy.chunk_ids = chunk_ids
        except Exception as e:
            logger.error(f"Failed to store vectors: {e}")
            # Continue without vectors - policy can still be used
        
        # Save policy
        self.store.save(policy)
        
        processing_time = (time.time() - start_time) * 1000
        logger.info(
            f"Policy created: {policy.policy_id} in {processing_time:.0f}ms"
        )
        
        return policy
    
    async def _store_policy_vectors(self, policy: Policy) -> List[str]:
        """Store policy text as vectors for RAG."""
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        
        # Split text into chunks
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        chunks = splitter.split_text(policy.raw_text)
        
        # Prepare documents with metadata
        documents = []
        for i, chunk in enumerate(chunks):
            documents.append({
                "content": chunk,
                "metadata": {
                    "policy_id": policy.policy_id,
                    "policy_number": policy.policy_number,
                    "policy_type": policy.policy_type.value,
                    "chunk_index": i,
                    "source": policy.source_filename or "policy"
                }
            })
        
        # Store in vector DB
        chunk_ids = self.embeddings.add_documents(documents)
        
        logger.info(f"Stored {len(chunk_ids)} vectors for policy {policy.policy_id}")
        return chunk_ids
    
    def get_policy(self, policy_id: str) -> Policy:
        """Get policy by ID."""
        policy = self.store.get(policy_id)
        if not policy:
            raise PolicyNotFoundError(policy_id)
        return policy
    
    def get_policy_by_number(self, policy_number: str) -> Policy:
        """Get policy by policy number."""
        policy = self.store.get_by_policy_number(policy_number)
        if not policy:
            raise PolicyNotFoundError(policy_number)
        return policy
    
    def list_policies(
        self,
        query: Optional[str] = None,
        policy_type: Optional[PolicyType] = None,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 10
    ) -> Tuple[List[PolicySummary], int]:
        """List policies with filtering."""
        policies, total = self.store.search(
            query=query,
            policy_type=policy_type,
            active_only=active_only,
            skip=skip,
            limit=limit
        )
        
        summaries = [
            PolicySummary(**p.to_summary())
            for p in policies
        ]
        
        return summaries, total
    
    def delete_policy(self, policy_id: str) -> bool:
        """Delete a policy."""
        policy = self.get_policy(policy_id)  # Raises if not found
        
        # Delete vectors
        if policy.chunk_ids:
            try:
                self.embeddings.delete_documents(policy.chunk_ids)
            except Exception as e:
                logger.error(f"Failed to delete vectors: {e}")
        
        # Delete policy
        return self.store.delete(policy_id)
    
    def get_expiring_policies(self, days: int = 30) -> List[PolicySummary]:
        """Get policies expiring soon."""
        policies = self.store.get_expiring_soon(days)
        return [PolicySummary(**p.to_summary()) for p in policies]


# Singleton
_policy_service: Optional[PolicyService] = None


def get_policy_service() -> PolicyService:
    """Get policy service singleton."""
    global _policy_service
    if _policy_service is None:
        _policy_service = PolicyService()
    return _policy_service