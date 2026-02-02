import asyncio
import time
import uuid
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from concurrent.futures import ThreadPoolExecutor

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore

from app.core.config import settings
from app.core.logging import get_logger
from app.models.schemas import ChatMessage, SourceDocument

logger = get_logger(__name__)

# ----------------------------
# Thread Pool
# ----------------------------
executor = ThreadPoolExecutor(max_workers=4)

# ----------------------------
# In-Memory Conversation Store
# ----------------------------
conversations: Dict[str, List[ChatMessage]] = {}

# ----------------------------
# Lazy Loading Instances
# ----------------------------
_embeddings: Optional[HuggingFaceEmbeddings] = None
_vectorstore: Optional[PineconeVectorStore] = None
_llm: Optional[Any] = None  # Changed from ChatGroq to Any


# ----------------------------
# Embeddings Manager
# ----------------------------
def get_embeddings() -> HuggingFaceEmbeddings:
    global _embeddings
    if _embeddings is None:
        logger.info("Initializing embeddings model...", model=settings.EMBEDDING_MODEL)
        _embeddings = HuggingFaceEmbeddings(
            model_name=settings.EMBEDDING_MODEL
        )
    return _embeddings


# ----------------------------
# Vector Store Manager
# ----------------------------
def get_vectorstore() -> PineconeVectorStore:
    global _vectorstore
    if _vectorstore is None:
        logger.info(f"Connecting to Pinecone index: {settings.PINECONE_INDEX_NAME}")
        _vectorstore = PineconeVectorStore(
            index_name=settings.PINECONE_INDEX_NAME,
            embedding=get_embeddings(),
            pinecone_api_key=settings.PINECONE_API_KEY
        )
    return _vectorstore


# ----------------------------
# LLM Manager (Multi-Provider)
# ----------------------------
def get_llm():
    """Get LLM instance based on configured provider."""
    global _llm
    if _llm is not None:
        return _llm
    
    provider = settings.LLM_PROVIDER.lower()
    
    if provider == "groq":
        logger.info("Initializing Groq LLM...", model=settings.GROQ_MODEL)
        from langchain_groq import ChatGroq
        _llm = ChatGroq(
            model_name=settings.GROQ_MODEL,
            api_key=settings.GROQ_API_KEY,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS
        )
    
    elif provider == "google":
        logger.info("Initializing Google Gemini LLM...", model=settings.GOOGLE_MODEL)
        from langchain_google_genai import ChatGoogleGenerativeAI
        _llm = ChatGoogleGenerativeAI(
            model=settings.GOOGLE_MODEL,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=settings.LLM_TEMPERATURE,
            max_output_tokens=settings.LLM_MAX_TOKENS,
            convert_system_message_to_human=True
        )
    
    elif provider == "ollama":
        logger.info("Initializing Ollama LLM...")
        from langchain_ollama import OllamaLLM
        _llm = OllamaLLM(
            model="llama3.2",
            temperature=settings.LLM_TEMPERATURE
        )
    
    else:
        raise ValueError(f"Unknown LLM provider: {provider}. Choose from: groq, google, ollama")
    
    return _llm


# ----------------------------
# RAG Prompt Template
# ----------------------------
RAG_PROMPT_TEMPLATE = """You are an intelligent document analysis assistant. Your task is to answer questions based ONLY on the provided context.

CONTEXT:
{context}

USER QUESTION: {question}

INSTRUCTIONS:
1. Answer ONLY based on the provided context
2. If the context doesn't contain enough information, say: "I cannot find this information in the provided documents."
3. Be precise and cite specific parts of the context when relevant
4. If asked about comparisons or analysis, structure your response clearly

ANSWER:"""


# ----------------------------
# Helper Functions
# ----------------------------
def format_docs(docs) -> str:
    """Format documents with source attribution."""
    formatted = []
    for i, doc in enumerate(docs, 1):
        source = doc.metadata.get('source', 'Unknown')
        page = doc.metadata.get('page', 'N/A')
        formatted.append(f"[Source {i}: {source}, Page {page}]\n{doc.page_content}")
    return "\n\n---\n\n".join(formatted)


def format_sources(docs) -> List[SourceDocument]:
    """Format documents into SourceDocument list."""
    return [
        SourceDocument(
            content=doc.page_content[:500],
            metadata=doc.metadata,
            score=getattr(doc, 'score', None)
        )
        for doc in docs
    ]


# ----------------------------
# Synchronous RAG Query
# ----------------------------
def query_rag_sync(
    question: str,
    k: int = 4,
    query_type: str = "similarity"
) -> dict:
    """Execute RAG query synchronously."""
    
    logger.info(f"Processing query: {question[:100]}...", k=k, query_type=query_type)
    
    try:
        vectorstore = get_vectorstore()
        llm = get_llm()
        
        # Retrieve documents
        logger.info("Retrieving relevant documents...")
        
        if query_type == "mmr":
            docs = vectorstore.max_marginal_relevance_search(question, k=k)
        else:
            docs = vectorstore.similarity_search(question, k=k)
        
        if not docs:
            logger.info("No relevant documents found")
            return {
                "success": True,
                "question": question,
                "answer": "No relevant documents found in the knowledge base. Please upload some documents first.",
                "sources": []
            }
        
        logger.info(f"Found {len(docs)} relevant documents")
        
        # Format context
        context = format_docs(docs)
        
        # Create and execute chain
        prompt = ChatPromptTemplate.from_template(RAG_PROMPT_TEMPLATE)
        chain = prompt | llm | StrOutputParser()
        
        logger.info("Generating answer with LLM...", provider=settings.LLM_PROVIDER)
        answer = chain.invoke({"context": context, "question": question})
        
        # Format sources
        sources = format_sources(docs)
        
        logger.info("Query processed successfully")
        
        return {
            "success": True,
            "question": question,
            "answer": answer,
            "sources": sources
        }
        
    except Exception as e:
        logger.exception(f"RAG query failed: {e}")
        return {
            "success": False,
            "question": question,
            "answer": None,
            "sources": None,
            "error": str(e)
        }


# ----------------------------
# Async Query Wrapper
# ----------------------------
async def query_rag(
    question: str,
    k: int = 4,
    query_type: str = "similarity",
    include_sources: bool = True
) -> dict:
    """Execute RAG query asynchronously."""
    
    start_time = time.time()
    loop = asyncio.get_event_loop()
    
    result = await loop.run_in_executor(
        executor,
        query_rag_sync,
        question,
        k,
        query_type
    )
    
    result["processing_time_ms"] = round((time.time() - start_time) * 1000, 2)
    
    if not include_sources:
        result["sources"] = None
    
    return result


# ----------------------------
# Chat with History (Sync)
# ----------------------------
def chat_sync(
    message: str,
    conversation_id: str,
    history: List[ChatMessage],
    k: int = 4
) -> dict:
    """Process chat message with history synchronously."""
    
    logger.info(f"Processing chat: {message[:100]}...", conversation_id=conversation_id)
    
    try:
        vectorstore = get_vectorstore()
        llm = get_llm()
        
        # Retrieve documents
        docs = vectorstore.similarity_search(message, k=k)
        context = format_docs(docs) if docs else "No relevant context found in documents."
        
        # Build conversation context (last 6 messages)
        conversation_context = ""
        for msg in history[-6:]:
            role = "User" if msg.role == "user" else "Assistant"
            conversation_context += f"{role}: {msg.content}\n"
        
        # Create prompt with history
        chat_prompt = f"""You are an intelligent document analysis assistant engaged in a conversation.

PREVIOUS CONVERSATION:
{conversation_context}

RELEVANT DOCUMENT CONTEXT:
{context}

CURRENT USER MESSAGE: {message}

INSTRUCTIONS:
- Continue the conversation naturally
- Use the document context to inform your answers
- If context doesn't help, be honest about it
- Maintain context from previous messages

YOUR RESPONSE:"""
        
        # Get response
        response = llm.invoke(chat_prompt)
        answer = response.content if hasattr(response, 'content') else str(response)
        
        # Update history
        new_history = history + [
            ChatMessage(role="user", content=message),
            ChatMessage(role="assistant", content=answer)
        ]
        
        # Store conversation
        conversations[conversation_id] = new_history
        
        return {
            "success": True,
            "conversation_id": conversation_id,
            "message": message,
            "answer": answer,
            "sources": format_sources(docs) if docs else [],
            "history": new_history
        }
        
    except Exception as e:
        logger.exception(f"Chat failed: {e}")
        return {
            "success": False,
            "conversation_id": conversation_id,
            "message": message,
            "answer": None,
            "error": str(e)
        }


# ----------------------------
# Async Chat Wrapper
# ----------------------------
async def chat(
    message: str,
    conversation_id: Optional[str] = None,
    history: Optional[List[ChatMessage]] = None,
    k: int = 4
) -> dict:
    """Process chat message asynchronously."""
    
    # Generate conversation ID if not provided
    if not conversation_id:
        conversation_id = str(uuid.uuid4())
    
    # Get history from store if not provided
    if history is None:
        history = conversations.get(conversation_id, [])
    
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        executor,
        chat_sync,
        message,
        conversation_id,
        history,
        k
    )