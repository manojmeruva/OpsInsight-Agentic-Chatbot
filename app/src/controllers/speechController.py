import asyncio
import base64
import os
import time
import tempfile

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from langchain_core.messages import HumanMessage


from core.llm_factory import get_codegen_llm
from core.message_serializer import content_text

router = APIRouter()

ALLOWED_EXTENSIONS = {"wav"}
MAX_AUDIO_BYTES = 10 * 1024 * 1024  # ~5 min of 16 kHz mono PCM


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@router.post("/speech-to-text")
async def speech_to_text(
    file: UploadFile = File(...),
    translate: str = Form(default="true"),
):
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail={"success": False, "error": "Empty filename"})

        if not allowed_file(file.filename):
            raise HTTPException(status_code=400, detail={"success": False, "error": "Invalid file type. Only WAV files are allowed"})

        if file.content_type and not file.content_type.startswith("audio/"):
            raise HTTPException(status_code=400, detail={"success": False, "error": f"Invalid content type: {file.content_type}. Expected audio file"})

        should_translate = translate.lower() == "true"

        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail={"success": False, "error": "Empty file uploaded"})

        if len(content) > MAX_AUDIO_BYTES:
            raise HTTPException(status_code=413, detail={"success": False, "error": "Recording is too long"})

        audio_b64 = base64.b64encode(content).decode("utf-8")

        llm = get_codegen_llm()

        # ── STT ───────────────────────────────────────────────────────────
        stt_message = HumanMessage(content=[
            {
                "type": "text",
                "text": (
                    "Transcribe the speech from this audio file. "
                    "Provide ONLY the exact transcription without any explanations, "
                    "commentary, or additional text. "
                    "If the audio is in Arabic, transcribe it in Arabic. "
                    "If it's in English, transcribe it in English."
                ),
            },
            {
                "type": "media",
                "mime_type": "audio/wav",
                "data": audio_b64,
            },
        ])

        # Blocking LLM calls run in a worker thread so other requests (and streams) keep flowing
        transcription = content_text((await asyncio.to_thread(llm.invoke, [stt_message])).content).strip()
        translation   = None

        # ── Translation ───────────────────────────────────────────────────
        if should_translate:
            tt_message = HumanMessage(content=(
                f"Translate the following text to English. "
                f"Provide ONLY the translation without any explanations, "
                f"commentary, or additional text:\n\n{transcription}"
            ))
            translation = content_text((await asyncio.to_thread(llm.invoke, [tt_message])).content).strip()

        return JSONResponse(
            status_code=200,
            content={
                "success":       True,
                "transcription": transcription,
                "translation":   translation,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)},
        )


