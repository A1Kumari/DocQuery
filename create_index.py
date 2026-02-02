import os
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("PINECONE_API_KEY")
index_name = os.getenv("PINECONE_INDEX_NAME", "docquery-index")

if not api_key:
    print("Error: PINECONE_API_KEY not found in environment variables.")
    exit(1)

pc = Pinecone(api_key=api_key)

if index_name not in pc.list_indexes().names():
    print(f"Index '{index_name}' not found. Creating...")
    try:
        pc.create_index(
            name=index_name,
            dimension=768,  # Google Embedding-001 dimension
            metric="cosine",
            spec=ServerlessSpec(
                cloud="aws",
                region="us-east-1"
            )
        )
        print(f"Index '{index_name}' created successfully.")
    except Exception as e:
        print(f"Failed to create index: {e}")
else:
    print(f"Index '{index_name}' already exists.")
