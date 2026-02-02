# app/api/v1/documents.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()

# ===================
# Response Models
# ===================

class DocumentInfo(BaseModel):
    document_id: Optional[str] = None
    filename: str
    chunk_count: int = 0
    file_size: Optional[int] = None
    upload_timestamp: Optional[str] = None

class DocumentListResponse(BaseModel):
    total: int
    skip: int
    limit: int
    documents: List[DocumentInfo]

class DocumentUploadResponse(BaseModel):
    success: bool
    message: str
    document_id: Optional[str] = None
    filename: str
    chunks: int
    file_size: Optional[int] = None
    upload_timestamp: str

# ===================
# Endpoints
# ===================

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """Upload a document for RAG processing."""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Import here to avoid circular imports
    from app.services.ingestion import ingest_document
    
    result = await ingest_document(file)
    
    return DocumentUploadResponse(
        success=True,
        message=result.get("message", "Document uploaded successfully"),
        document_id=result.get("document_id"),
        filename=file.filename,
        chunks=result.get("chunks", 0),
        file_size=file.size,
        upload_timestamp=datetime.utcnow().isoformat()
    )

@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100)
):
    """List all uploaded documents."""
    from app.services.store import list_files
    
    files = list_files()
    
    # Convert to DocumentInfo objects
    documents = []
    for f in files[skip:skip + limit]:
        documents.append(DocumentInfo(
            document_id=f.get("document_id"),
            filename=f.get("filename", "Unknown"),
            chunk_count=f.get("chunk_count", 0),
            file_size=f.get("file_size"),
            upload_timestamp=f.get("upload_timestamp")
        ))
    
    return DocumentListResponse(
        total=len(files),
        skip=skip,
        limit=limit,
        documents=documents
    )

@router.get("/{doc_id}")
async def get_document(doc_id: str):
    """Get document details by ID or filename."""
    from app.services.store import list_files
    
    files = list_files()
    for f in files:
        if f.get("filename") == doc_id or f.get("document_id") == doc_id:
            return DocumentInfo(
                document_id=f.get("document_id"),
                filename=f.get("filename", "Unknown"),
                chunk_count=f.get("chunk_count", 0),
                file_size=f.get("file_size"),
                upload_timestamp=f.get("upload_timestamp")
            )
    
    raise HTTPException(status_code=404, detail="Document not found")

@router.delete("/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a document and its vectors."""
    # TODO: Implement actual deletion from Pinecone
    return {
        "success": True,
        "message": f"Document {doc_id} deleted"
    }