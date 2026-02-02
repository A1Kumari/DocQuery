# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings

# ===================
# Lifespan Management
# ===================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown."""
    print(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"📦 LLM Provider: {settings.LLM_PROVIDER}")
    yield
    print("👋 Shutting down...")

# ===================
# Application Setup
# ===================

app = FastAPI(
    title=settings.APP_NAME,
    description="Insurance Claim Validation System with Graph RAG",
    version=settings.APP_VERSION,
    lifespan=lifespan
)

# ===================
# CORS Middleware
# ===================

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===================
# Include Routers
# ===================

# Legacy router (your existing endpoints)
from app.api.endpoints import router as legacy_router
app.include_router(legacy_router, prefix="/api", tags=["legacy"])

# V1 API Routers
from app.api.v1.document import router as documents_router
from app.api.v1.policies import router as policies_router
from app.api.v1.claims import router as claims_router
from app.api.v1.chat import router as chat_router
from app.api.v1.admin import router as admin_router
from app.api.v1.dashboard import router as dashboard_router  # NEW!

app.include_router(documents_router, prefix="/api/v1/documents", tags=["documents"])
app.include_router(policies_router, prefix="/api/v1/policies", tags=["policies"])
app.include_router(claims_router, prefix="/api/v1/claims", tags=["claims"])
app.include_router(chat_router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(admin_router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(dashboard_router, prefix="/api/v1/dashboard", tags=["dashboard"])  # NEW!

# ===================
# Root Endpoints
# ===================

@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "endpoints": {
            "legacy": "/api",
            "documents": "/api/v1/documents",
            "policies": "/api/v1/policies",
            "claims": "/api/v1/claims",
            "chat": "/api/v1/chat",
            "dashboard": "/api/v1/dashboard",
            "admin": "/api/v1/admin"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": settings.APP_VERSION}