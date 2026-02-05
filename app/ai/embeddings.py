# app/ai/embeddings.py
"""Embedding service for vector operations."""

from typing import List, Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore

from app.core.config import settings
from app.core.logging import get_logger
from app.core.exceptions import PineconeConnectionError

logger = get_logger(__name__)

_executor = ThreadPoolExecutor(max_workers=2)


class EmbeddingService:
    """Service for generating embeddings and vector operations."""
    
    def __init__(self):
        self._embeddings: Optional[HuggingFaceEmbeddings] = None
        self._vectorstore: Optional[PineconeVectorStore] = None
    
    @property
    def embeddings(self) -> HuggingFaceEmbeddings:
        """Get embeddings model."""
        if self._embeddings is None:
            logger.info(f"Initializing embeddings: {settings.EMBEDDING_MODEL}")
            self._embeddings = HuggingFaceEmbeddings(
                model_name=settings.EMBEDDING_MODEL
            )
        return self._embeddings
    
    @property
    def vectorstore(self) -> PineconeVectorStore:
        """Get Pinecone vector store."""
        if self._vectorstore is None:
            try:
                logger.info(f"Connecting to Pinecone index: {settings.PINECONE_INDEX_NAME}")
                self._vectorstore = PineconeVectorStore(
                    index_name=settings.PINECONE_INDEX_NAME,
                    embedding=self.embeddings,
                    pinecone_api_key=settings.PINECONE_API_KEY
                )
            except Exception as e:
                raise PineconeConnectionError(str(e))
        return self._vectorstore
    
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        return self.embeddings.embed_query(text)
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        return self.embeddings.embed_documents(texts)
    
    async def embed_text_async(self, text: str) -> List[float]:
        """Async embedding generation."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, self.embed_text, text)
    
    def similarity_search(
        self, 
        query: str, 
        k: int = 4,
        filter: Optional[dict] = None
    ) -> List[dict]:
        """Search for similar documents."""
        docs = self.vectorstore.similarity_search(
            query=query,
            k=k,
            filter=filter
        )
        return [
            {
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": getattr(doc, 'score', None)
            }
            for doc in docs
        ]
    
    def similarity_search_with_score(
        self, 
        query: str, 
        k: int = 4,
        filter: Optional[dict] = None
    ) -> List[dict]:
        """Search with relevance scores."""
        results = self.vectorstore.similarity_search_with_score(
            query=query,
            k=k,
            filter=filter
        )
        return [
            {
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": score
            }
            for doc, score in results
        ]
    
    async def similarity_search_async(
        self, 
        query: str, 
        k: int = 4,
        filter: Optional[dict] = None
    ) -> List[dict]:
        """Async similarity search."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor,
            lambda: self.similarity_search(query, k, filter)
        )
    
    def add_documents(
        self, 
        documents: List[dict],
        namespace: Optional[str] = None
    ) -> List[str]:
        """
        Add documents to vector store.
        
        Args:
            documents: List of {"content": str, "metadata": dict}
            namespace: Optional namespace for organization
        
        Returns:
            List of document IDs
        """
        from langchain_core.documents import Document
        
        docs = [
            Document(
                page_content=d["content"],
                metadata=d.get("metadata", {})
            )
            for d in documents
        ]
        
        ids = self.vectorstore.add_documents(docs)
        logger.info(f"Added {len(ids)} documents to vector store")
        return ids
    
    def delete_documents(self, ids: List[str]) -> bool:
        """Delete documents by IDs."""
        try:
            self.vectorstore.delete(ids)
            logger.info(f"Deleted {len(ids)} documents from vector store")
            return True
        except Exception as e:
            logger.error(f"Failed to delete documents: {e}")
            return False


# Singleton instance
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Get the embedding service singleton."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service