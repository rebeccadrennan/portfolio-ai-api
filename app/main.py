from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from app.models.chat import ChatRequest, ChatResponse
from app.models.voice import SpeechToTextResponse, TextToSpeechRequest
from app.services.elevenlabs_service import (
    MAX_TTS_TEXT_LENGTH,
    SUPPORTED_AUDIO_TYPES,
    ElevenLabsConfigurationError,
    ElevenLabsService,
    ElevenLabsTimeoutError,
    ElevenLabsUpstreamError,
    ElevenLabsValidationError,
)
from app.services.gemini_service import GeminiService, GeminiServiceError

app = FastAPI(title="Rebecca Drennan Portfolio AI API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

chat_service = GeminiService()
voice_service = ElevenLabsService()


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "portfolio-ai-api",
    }


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    if not request.message.strip():
        raise HTTPException(
            status_code=400,
            detail="Please provide a non-empty message in the 'message' field.",
        )

    try:
        reply = chat_service.generate_reply(request.message)
    except GeminiServiceError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return ChatResponse(reply=reply)


def _raise_voice_http_error(exc: Exception) -> None:
    if isinstance(exc, ElevenLabsValidationError):
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if isinstance(exc, ElevenLabsConfigurationError):
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if isinstance(exc, ElevenLabsTimeoutError):
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    if isinstance(exc, ElevenLabsUpstreamError):
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    raise HTTPException(status_code=500, detail="Voice processing failed.") from exc


@app.post("/speech-to-text", response_model=SpeechToTextResponse)
async def speech_to_text(audio: UploadFile | None = File(default=None)) -> SpeechToTextResponse:
    if audio is None:
        raise HTTPException(status_code=400, detail="Please attach an audio file in the 'audio' field.")

    content_type = (audio.content_type or "").split(";", 1)[0].strip().lower()
    if content_type not in SUPPORTED_AUDIO_TYPES:
        accepted_types = ", ".join(sorted(SUPPORTED_AUDIO_TYPES))
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported audio type '{audio.content_type or 'unknown'}'. Supported types: {accepted_types}.",
        )

    audio_bytes = await audio.read()
    await audio.close()

    try:
        text = await voice_service.transcribe_audio(
            filename=audio.filename or "recording.webm",
            content_type=content_type,
            audio_bytes=audio_bytes,
        )
    except Exception as exc:
        _raise_voice_http_error(exc)

    return SpeechToTextResponse(text=text)


@app.post("/text-to-speech")
async def text_to_speech(request: TextToSpeechRequest) -> Response:
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Please provide non-empty text in the 'text' field.")
    if len(text) > MAX_TTS_TEXT_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Text exceeds the maximum length of {MAX_TTS_TEXT_LENGTH} characters.",
        )

    try:
        audio_bytes, media_type = await voice_service.generate_speech_audio(text)
    except Exception as exc:
        _raise_voice_http_error(exc)

    return Response(
        content=audio_bytes,
        media_type=media_type,
        headers={"Cache-Control": "no-store"},
    )
