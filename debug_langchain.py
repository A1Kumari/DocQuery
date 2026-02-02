import sys
print(f"Python executable: {sys.executable}")
print(f"Python version: {sys.version}")

try:
    import langchain
    print(f"LangChain version: {getattr(langchain, '__version__', 'Unknown')}")
    print(f"LangChain file: {langchain.__file__}")
except ImportError:
    print("LangChain not installed")

try:
    import langchain.chains
    print("langchain.chains imported successfully")
except ImportError as e:
    print(f"Failed to import langchain.chains: {e}")

try:
    from langchain.chains import create_retrieval_chain
    print("create_retrieval_chain imported successfully")
except ImportError as e:
    print(f"Failed to import create_retrieval_chain: {e}")
