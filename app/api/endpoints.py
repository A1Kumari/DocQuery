from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from app.services.ingestion import ingest_document
from app.services.rag import query_rag

router = APIRouter()

class QueryRequest(BaseModel):
    question: str

@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    return await ingest_document(file)

@router.post("/query")
async def ask_question(request: QueryRequest):
    return await query_rag(request.question)
