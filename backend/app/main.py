from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.health import router as health_router
from app.api.documents import router as documents_router
from app.api.generation import router as generation_router
from app.api.providers import router as providers_router
from app.db.database import init_db

app = FastAPI(
    title="TestPilot Lite RAG Backend",
    description="AI Test Scenario Generator using RAG",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    init_db()

app.include_router(health_router, prefix="/api")
app.include_router(documents_router, prefix="/api")
app.include_router(generation_router, prefix="/api")
app.include_router(providers_router, prefix="/api")

@app.get("/", summary="Root Endpoint")
def root():
    return {
        "message": "TestPilot Lite RAG backend is running.",
        "docs": "/docs"
    }
