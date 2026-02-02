import os
import shutil
import tempfile
import logging

from fastapi import UploadFile, HTTPException
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore

from app.core.config import settings

# ----------------------------
# Logging Setup
# ----------------------------
logger = logging.getLogger("ingestion")
logging.basicConfig(level=logging.INFO)

# ----------------------------
# Validate Environment Variables
# ----------------------------
if not settings.GOOGLE_API_KEY:
    raise RuntimeError("GOOGLE_API_KEY is missing in environment variables")

if not settings.PINECONE_API_KEY:
    raise RuntimeError("PINECONE_API_KEY is missing in environment variables")

if not settings.PINECONE_INDEX_NAME:
    raise RuntimeError("PINECONE_INDEX_NAME is missing in environment variables")

# ----------------------------
# Initialize Embeddings ONCE
# ----------------------------
logger.info("Initializing embeddings...")
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

# ----------------------------
# Initialize Pinecone VectorStore ONCE
# ----------------------------
logger.info("Connecting to Pinecone index: %s", settings.PINECONE_INDEX_NAME)

vectorstore = PineconeVectorStore(
    index_name=settings.PINECONE_INDEX_NAME,
    embedding=embeddings,
    pinecone_api_key=settings.PINECONE_API_KEY
)

# ----------------------------
# Main Ingestion Function
# ----------------------------
async def ingest_document(file: UploadFile):
    tmp_path = None

    logger.info("Received file: %s", file.filename)

    # ----------------------------
    # Save Uploaded File
    # ----------------------------
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            tmp_path = tmp_file.name

        logger.info("Saved temp file at: %s", tmp_path)

    except Exception as e:
        logger.exception("Failed to save uploaded file")
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    try:
        # ----------------------------
        # Load PDF
        # ----------------------------
        logger.info("Loading PDF...")
        loader = PyPDFLoader(tmp_path)
        documents = loader.load()

        if not documents:
            raise ValueError("No text could be extracted from PDF")

        logger.info("Loaded %d pages", len(documents))

        # ----------------------------
        # Split into Chunks
        # ----------------------------
        logger.info("Splitting into chunks...")
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            add_start_index=True
        )

        chunks = text_splitter.split_documents(documents)

        logger.info("Created %d chunks", len(chunks))

        # ----------------------------
        # Add Metadata
        # ----------------------------
        for i, chunk in enumerate(chunks):
            chunk.metadata["source"] = file.filename
            chunk.metadata["chunk_id"] = i

        # ----------------------------
        # Store in Pinecone
        # ----------------------------
        logger.info("Uploading chunks to Pinecone...")
        vectorstore.add_documents(chunks)

        logger.info("Upload successful")

        # ----------------------------
        # Save Metadata
        # ----------------------------
        from app.services.store import add_file_metadata
        add_file_metadata({
            "filename": file.filename,
            "chunk_count": len(chunks),
            "file_size": file.size
        })

        return {
            "message": f"Successfully ingested {len(chunks)} chunks from {file.filename}",
            "chunks": len(chunks)
        }

    except Exception as e:
        logger.exception("Ingestion failed")
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # ----------------------------
        # Cleanup Temp File
        # ----------------------------
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
            logger.info("Deleted temp file")