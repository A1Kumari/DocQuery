import os
from typing import List
from fastapi import UploadFile, HTTPException
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from app.core.config import settings
import shutil
import tempfile

# Initialize Embeddings
embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=settings.GOOGLE_API_KEY)

async def ingest_document(file: UploadFile):
    # Save uploaded file to a temporary file
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            tmp_path = tmp_file.name
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    try:
        # Load Document
        loader = PyPDFLoader(tmp_path)
        documents = loader.load()

        # Split Document
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            add_start_index=True
        )
        chunks = text_splitter.split_documents(documents)

        # Add Metadata (Source, Page) is handled by PyPDFLoader mostly, but we can enhance if needed
        for i, chunk in enumerate(chunks):
            chunk.metadata["source"] = file.filename
            chunk.metadata["chunk_id"] = i

        # Index to Pinecone
        # Ensure index exists? Langchain might handle or error. We assume it exists per plan.
        PineconeVectorStore.from_documents(
            documents=chunks,
            embedding=embeddings,
            index_name=settings.PINECONE_INDEX_NAME,
            pinecone_api_key=settings.PINECONE_API_KEY
        )
        
        return {"message": f"Successfully ingested {len(chunks)} chunks from {file.filename}", "chunks": len(chunks)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")
    finally:
        os.remove(tmp_path)
