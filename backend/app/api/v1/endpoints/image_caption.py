from fastapi import APIRouter, UploadFile, File
from fastapi import HTTPException

router = APIRouter()

@router.post("/image-caption")
async def caption_image(file: UploadFile = File(...)):
    del file
    raise HTTPException(
        status_code=501,
        detail="Image captioning is not enabled in the modernized API yet.",
    )
