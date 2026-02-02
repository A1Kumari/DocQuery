# app/routers/policies.py
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.parsers.pdf_parser import PDFParser
from app.parsers.policy_extractor import PolicyExtractor
from app.database.neo4j_client import Neo4jClient
from app.database.pinecone_client import PineconeClient
from app.models.policy import PolicyDocument
import uuid

router = APIRouter(prefix="/policies", tags=["policies"])

@router.post("/upload", response_model=PolicyDocument)
async def upload_policy(
    file: UploadFile = File(...),
    policy_type: str = "health",
    holder_name: str = ""
):
    """Upload and process a policy document."""
    
    # Parse PDF
    pdf_parser = PDFParser()
    text = await pdf_parser.extract_text(file)
    
    # Extract structured information
    extractor = PolicyExtractor()
    policy_id = str(uuid.uuid4())
    
    policy = await extractor.extract_full_policy(
        text=text,
        policy_id=policy_id,
        metadata={
            "policy_number": f"POL-{policy_id[:8]}",
            "policy_type": policy_type,
            "holder_name": holder_name,
            "effective_date": "2024-01-01",
            "expiration_date": "2025-01-01"
        }
    )
    
    # Store in Neo4j
    neo4j = Neo4jClient()
    await neo4j.create_policy_graph(policy)
    await neo4j.close()
    
    # Store vectors in Pinecone
    pinecone = PineconeClient()
    chunk_ids = await pinecone.store_policy(policy)
    policy.chunk_ids = chunk_ids
    
    return policy

@router.get("/{policy_id}/graph")
async def get_policy_graph(policy_id: str):
    """Get policy graph for visualization."""
    neo4j = Neo4jClient()
    graph = await neo4j.get_policy_graph(policy_id)
    await neo4j.close()
    
    if not graph:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    return graph