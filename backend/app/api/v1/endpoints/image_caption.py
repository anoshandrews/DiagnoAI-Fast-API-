from fastapi import APIRouter, UploadFile, File
from app.services.image_captioning import run_inference

router = APIRouter()

@router.post("/image-caption")
async def caption_image(file: UploadFile = File(...)):
    result = run_inference(file.file)
    return {"caption": result}