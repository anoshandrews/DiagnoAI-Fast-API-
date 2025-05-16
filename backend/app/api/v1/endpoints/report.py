from fastapi import APIRouter, UploadFile, File
from app.services import report_generator
from typing import List
import shutil
import os

router = APIRouter()

@router.post("/generate_report/")
async def generate_report(chat_history: List[str]):
    """
    Accepts a list of user messages and returns a medical report.
    """
    summary = report_generator.summarize_chat(chat_history)
    context = report_generator.retrieve_context(summary)
    report = report_generator.build_report(summary, context)
    return {"report": report}

@router.post("/analyze_image/")
async def analyze_image(file: UploadFile = File(...)):
    """
    Analyzes an uploaded image and returns a medical caption.
    """
    temp_path = f"/tmp/{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    result = report_generator.run_inference(temp_path)
    os.remove(temp_path)
    return {"caption": result}