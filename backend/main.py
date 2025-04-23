from fastapi import FastAPI
from app.api.v1.endpoints import chat
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="DiagnoAI",
    version="1.0.0",
    description="Your AI medical assistant"
)

# CORS setup to allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # you can restrict this later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(chat.router, prefix="/api/v1", tags=["chat"])   