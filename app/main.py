from fastapi import FastAPI
from app.core.config import settings

app = FastAPI(title="DocQuery API")

@app.get("/")
def read_root():
    return {"message": "Welcome to DocQuery API"}

from app.api.endpoints import router as api_router

app.include_router(api_router, prefix="/api")
