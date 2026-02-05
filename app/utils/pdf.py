# app/utils/pdf.py
"""PDF text extraction utilities."""

import tempfile
import shutil
import os
from typing import Tuple

from fastapi import UploadFile
from langchain_community.document_loaders import PyPDFLoader

from app.core.logging import get_logger

logger = get_logger(__name__)


async def extract_text_from_pdf(file: UploadFile) -> Tuple[str, int]:
    """
    Extract text content from a PDF file.
    
    Args:
        file: FastAPI UploadFile object
        
    Returns:
        Tuple of (extracted_text, page_count)
        
    Raises:
        ValueError: If PDF cannot be processed
    """
    tmp_path = None
    
    try:
        # Save uploaded file to temp location
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            tmp_path = tmp_file.name
        
        logger.info(f"Processing PDF: {file.filename}")
        
        # Load and extract text
        loader = PyPDFLoader(tmp_path)
        pages = loader.load()
        
        if not pages:
            raise ValueError("No content could be extracted from PDF")
        
        # Combine all pages
        full_text = "\n\n".join([page.page_content for page in pages])
        page_count = len(pages)
        
        logger.info(f"Extracted {page_count} pages, {len(full_text)} characters")
        
        return full_text, page_count
        
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        raise ValueError(f"Failed to process PDF: {str(e)}")
        
    finally:
        # Cleanup temp file
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
            
        # Reset file pointer for potential reuse
        await file.seek(0)