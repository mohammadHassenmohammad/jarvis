from fastapi import APIRouter, UploadFile, File, HTTPException
from ..services.whisper_service import whisper_service

router = APIRouter(prefix="/api/voice", tags=["voice"])

@router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """
    Accepts raw audio from the frontend (webm, wav, etc.)
    and returns high-accuracy Whisper transcription.
    """
    try:
        audio_bytes = await file.read()
        if not audio_bytes:
            return {"text": "", "confidence": 1.0}

        text = whisper_service.transcribe(audio_bytes, filename=file.filename or "audio.webm")
        return {"text": text, "status": "success"}
    except Exception as e:
        print(f"[!] Error in Whisper transcription: {e}")
        raise HTTPException(status_code=500, detail=str(e))
