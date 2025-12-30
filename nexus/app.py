from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from modules.chat_endpoints import router as chat_router
from modules.database import connect_to_db, disconnect_from_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_to_db()
    yield
    # Shutdown
    await disconnect_from_db()

app = FastAPI(title="Mobius Nexus", version="0.1.0", lifespan=lifespan)

# CORS Configuration
origins = [
    "http://localhost:3000", # Portal
    "chrome-extension://*",  # Spectacles (Extension)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the Chat Module
app.include_router(chat_router, prefix="/api/chat", tags=["Chat"])

@app.get("/")
async def root():
    return {"status": "online", "system": "Mobius Nexus"}
