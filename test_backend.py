import requests
import sys

BASE_URL = "http://localhost:8000/api"

def test_root():
    try:
        r = requests.get("http://localhost:8000/")
        assert r.status_code == 200
        print("✅ Root endpoint operational")
    except Exception as e:
        print(f"❌ Root endpoint failed: {e}")
        sys.exit(1)

def test_query():
    # This expects the server to be running and Pinecone to be accessible
    payload = {"question": "What is this system?"}
    try:
        r = requests.post(f"{BASE_URL}/query", json=payload)
        if r.status_code == 200:
            print("✅ Query endpoint operational")
            print("Response:", r.json())
        else:
            print(f"⚠️ Query endpoint returned {r.status_code}: {r.text}")
    except Exception as e:
        print(f"❌ Query endpoint failed: {e}")

if __name__ == "__main__":
    test_root()
    test_query()
