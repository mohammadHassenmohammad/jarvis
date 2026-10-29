from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .config import settings
from .database.db import init_db
from .api import chat, conversations, memories, tools, settings as settings_api, voice

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database and tables
    init_db()
    print(f"[*] JARVIS Backend Initialized. Database at: {settings.DB_PATH}")
    yield
    print("[*] JARVIS Backend Shutting Down.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Conversation-Id"]
)

# Register API Routers
app.include_router(chat.router)
app.include_router(conversations.router)
app.include_router(memories.router)
app.include_router(tools.router)
app.include_router(settings_api.router)
app.include_router(voice.router)

@app.get("/")
def root():
    return {
        "status": "online",
        "system": "J.A.R.V.I.S.",
        "version": settings.VERSION,
        "message": "All systems operational, Sir."
    }

@app.get("/api/health")
def health():
    return {
        "status": "healthy",
        "system": "J.A.R.V.I.S.",
        "version": settings.VERSION
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
