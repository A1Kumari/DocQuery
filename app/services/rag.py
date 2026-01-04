from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from app.core.config import settings

# Initialize LLM and Embeddings
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=settings.GOOGLE_API_KEY, temperature=0)
embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=settings.GOOGLE_API_KEY)

# Vector Store
vectorstore = PineconeVectorStore(
    index_name=settings.PINECONE_INDEX_NAME,
    embedding=embeddings,
    pinecone_api_key=settings.PINECONE_API_KEY
)

# Retrieval Chain
retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

system_prompt = (
    "You are an assistant for question-answering tasks. "
    "Use the following pieces of retrieved context to answer "
    "the question. If you don't know the answer, say that you "
    "don't know. Use three sentences maximum and keep the "
    "answer concise."
    "\n\n"
    "{context}"
)

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        ("human", "{input}"),
    ]
)

question_answer_chain = create_stuff_documents_chain(llm, prompt)
rag_chain = create_retrieval_chain(retriever, question_answer_chain)

async def query_rag(question: str):
    response = rag_chain.invoke({"input": question})
    return {
        "answer": response["answer"],
        "context": [doc.page_content for doc in response["context"]],
        "citations": [doc.metadata for doc in response["context"]] # Return metadata for citations
    }
