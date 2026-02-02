from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ----------------------------
# Enums
# ----------------------------
class QueryType(str, Enum):
    SIMILARITY = "similarity"
    MMR = "mmr"


# ----------------------------
# Source Document
# ----------------------------
class SourceDocument(BaseModel):
    content: str
    metadata: Dict[str, Any]
    score: Optional[float] = None


# ----------------------------
# Chat Message
# ----------------------------
class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


# ----------------------------
# Query Request/Response
# ----------------------------
class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    k: int = Field(default=4, ge=1, le=10)
    query_type: QueryType = Field(default=QueryType.SIMILARITY)
    include_sources: bool = Field(default=True)


class QueryResponse(BaseModel):
    success: bool
    question: str
    answer: Optional[str] = None
    sources: Optional[List[SourceDocument]] = None
    processing_time_ms: Optional[float] = None
    error: Optional[str] = None


# ----------------------------
# Chat Request/Response
# ----------------------------
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    conversation_id: Optional[str] = None
    history: Optional[List[ChatMessage]] = Field(default_factory=list)
    k: int = Field(default=4, ge=1, le=10)


class ChatResponse(BaseModel):
    success: bool
    conversation_id: str
    message: str
    answer: Optional[str] = None
    sources: Optional[List[SourceDocument]] = None
    history: Optional[List[ChatMessage]] = None
    error: Optional[str] = None


# ----------------------------
# Ingest Request/Response
# ----------------------------
class IngestResponse(BaseModel):
    success: bool
    message: str
    filename: Optional[str] = None
    file_size_bytes: Optional[int] = None
    pages: Optional[int] = None
    chunks: Optional[int] = None
    processing_time_ms: Optional[float] = None
    document_id: Optional[str] = None


# ----------------------------
# Document Management
# ----------------------------
class DocumentInfo(BaseModel):
    document_id: str
    filename: str
    pages: int
    chunks: int
    uploaded_at: datetime
    file_size_bytes: int


class DocumentListResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    documents: List[DocumentInfo]
    total_count: int


class DeleteDocumentResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    document_id: str
    chunks_deleted: int


# ----------------------------
# Health Check
# ----------------------------
class ServiceStatus(BaseModel):
    name: str
    status: str  # "healthy", "unhealthy", "degraded"
    latency_ms: Optional[float] = None
    details: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    services: List[ServiceStatus]
    timestamp: datetime = Field(default_factory=datetime.utcnow)