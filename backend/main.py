"""
Main entry point for the FastAPI backend.

This module initializes the FastAPI app, includes API routers,
and configures any necessary middleware or startup events.
"""


from fastapi import FastAPI
from app.api.v1.endpoints import chat
# from app.api.v1.endpoints import image_caption
from app.api.v1.endpoints import report
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
# app.include_router(image_caption.router, prefix="/api/v1")
app.include_router(report.router, prefix = "/report", tags = ['Report'])
