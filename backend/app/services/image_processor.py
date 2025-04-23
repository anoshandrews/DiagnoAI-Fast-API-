import whisper
import tempfile
from fastapi import UploadFile

model = whisper.load_model("base")

async def process_image(file: UploadFile) -> str:
    with tempfile.NamedTemporaryFile(delete=False) as temp:
        temp.write(await file.read())
        result = model.transcribe(temp.name)
    return result.get("text", "Could not transcribe")