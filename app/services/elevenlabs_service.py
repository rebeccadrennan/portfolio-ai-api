from __future__ import annotations

import os
from collections.abc import Callable

import httpx
from dotenv import load_dotenv

load_dotenv()

SUPPORTED_AUDIO_TYPES = {
    "audio/mp4",
    "audio/ogg",
    "audio/wav",
    "audio/webm",
}
MAX_AUDIO_BYTES = 10 * 1024 * 1024
MAX_TTS_TEXT_LENGTH = 4000
DEFAULT_STT_MODEL_ID = "scribe_v2"
DEFAULT_TTS_MODEL_ID = "eleven_multilingual_v2"
DEFAULT_TTS_OUTPUT_FORMAT = "mp3_44100_128"
API_BASE_URL = "https://api.elevenlabs.io/v1"


class ElevenLabsServiceError(RuntimeError):
    """Base error for ElevenLabs proxy failures."""


class ElevenLabsConfigurationError(ElevenLabsServiceError):
    """Raised when required ElevenLabs configuration is missing."""


class ElevenLabsValidationError(ElevenLabsServiceError):
    """Raised when a request fails local validation before hitting ElevenLabs."""


class ElevenLabsTimeoutError(ElevenLabsServiceError):
    """Raised when ElevenLabs does not respond within the configured timeout."""


class ElevenLabsUpstreamError(ElevenLabsServiceError):
    """Raised when ElevenLabs returns an unexpected response."""


class ElevenLabsService:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        voice_id: str | None = None,
        stt_model_id: str = DEFAULT_STT_MODEL_ID,
        tts_model_id: str | None = None,
        tts_output_format: str = DEFAULT_TTS_OUTPUT_FORMAT,
        max_audio_bytes: int = MAX_AUDIO_BYTES,
        max_tts_text_length: int = MAX_TTS_TEXT_LENGTH,
        client_factory: Callable[..., httpx.AsyncClient] | None = None,
    ) -> None:
        self.api_key = (api_key or os.getenv("ELEVENLABS_API_KEY", "")).strip()
        self.voice_id = (voice_id or os.getenv("ELEVENLABS_VOICE_ID", "")).strip()
        self.stt_model_id = stt_model_id
        self.tts_model_id = (tts_model_id or os.getenv("ELEVENLABS_TTS_MODEL_ID", "")).strip()
        self.tts_output_format = tts_output_format
        self.max_audio_bytes = max_audio_bytes
        self.max_tts_text_length = max_tts_text_length
        self._client_factory = client_factory or httpx.AsyncClient

    async def transcribe_audio(
        self,
        *,
        filename: str,
        content_type: str,
        audio_bytes: bytes,
    ) -> str:
        self._require_api_key()

        if not audio_bytes:
            raise ElevenLabsValidationError("The uploaded audio file is empty.")
        if len(audio_bytes) > self.max_audio_bytes:
            raise ElevenLabsValidationError(
                f"Audio exceeds the maximum upload size of {self.max_audio_bytes // (1024 * 1024)} MB."
            )

        response = await self._post(
            "/speech-to-text",
            data={"model_id": self.stt_model_id},
            files={"file": (filename, audio_bytes, content_type)},
            timeout=httpx.Timeout(30.0, connect=5.0, read=30.0, write=30.0),
            failure_message="Speech-to-text request failed.",
            timeout_message="Speech-to-text request timed out.",
        )

        text = response.json().get("text")
        if not isinstance(text, str) or not text.strip():
            raise ElevenLabsUpstreamError(
                "Speech-to-text returned an invalid transcription payload."
            )

        return text.strip()

    async def generate_speech_audio(self, text: str) -> tuple[bytes, str]:
        self._require_api_key()
        self._require_voice_id()

        cleaned_text = text.strip()
        if not cleaned_text:
            raise ElevenLabsValidationError("Cannot generate speech for empty text.")
        if len(cleaned_text) > self.max_tts_text_length:
            raise ElevenLabsValidationError(
                f"Text exceeds the maximum length of {self.max_tts_text_length} characters."
            )

        response = await self._post(
            f"/text-to-speech/{self.voice_id}/stream",
            params={"output_format": self.tts_output_format},
            json={"text": cleaned_text, "model_id": self._get_tts_model_id()},
            timeout=httpx.Timeout(45.0, connect=5.0, read=45.0, write=30.0),
            failure_message="Text-to-speech request failed.",
            timeout_message="Text-to-speech request timed out.",
        )

        media_type = response.headers.get("content-type", "audio/mpeg")
        audio_bytes = response.content
        if not audio_bytes:
            raise ElevenLabsUpstreamError("Text-to-speech returned an empty audio response.")

        return audio_bytes, media_type

    async def _post(self, path: str, **kwargs: object) -> httpx.Response:
        timeout = kwargs.pop("timeout")
        failure_message = str(kwargs.pop("failure_message"))
        timeout_message = str(kwargs.pop("timeout_message"))

        try:
            async with self._client_factory(
                base_url=API_BASE_URL,
                headers={"xi-api-key": self.api_key},
                timeout=timeout,
            ) as client:
                response = await client.post(path, **kwargs)
        except httpx.TimeoutException as exc:
            raise ElevenLabsTimeoutError(timeout_message) from exc
        except httpx.HTTPError as exc:
            raise ElevenLabsUpstreamError(failure_message) from exc

        if response.status_code >= 400:
            detail = self._extract_error_detail(response)
            raise ElevenLabsUpstreamError(f"{failure_message} {detail}")

        return response

    def _get_tts_model_id(self) -> str:
        if self.tts_model_id:
            return self.tts_model_id
        return DEFAULT_TTS_MODEL_ID

    def _require_api_key(self) -> None:
        if not self.api_key:
            raise ElevenLabsConfigurationError(
                "ELEVENLABS_API_KEY is missing. Add it to your backend environment before using voice endpoints."
            )

    def _require_voice_id(self) -> None:
        if not self.voice_id:
            raise ElevenLabsConfigurationError(
                "ELEVENLABS_VOICE_ID is missing. Add it to your backend environment before using text-to-speech."
            )

    @staticmethod
    def _extract_error_detail(response: httpx.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            payload = None

        payload_detail = ElevenLabsService._stringify_error_payload(payload)
        if payload_detail:
            return ElevenLabsService._append_request_id(payload_detail, response)

        text_detail = (response.text or "").strip()
        if text_detail:
            return ElevenLabsService._append_request_id(text_detail[:300], response)

        fallback = f"ElevenLabs returned status {response.status_code}."
        return ElevenLabsService._append_request_id(fallback, response)

    @staticmethod
    def _stringify_error_payload(payload: object) -> str:
        if isinstance(payload, str):
            return payload.strip()[:300]

        if isinstance(payload, dict):
            for key in ("detail", "message", "error", "text"):
                value = payload.get(key)
                detail = ElevenLabsService._stringify_error_payload(value)
                if detail:
                    return detail

        if isinstance(payload, list):
            parts = [
                detail
                for item in payload
                if (detail := ElevenLabsService._stringify_error_payload(item))
            ]
            if parts:
                return "; ".join(parts)[:300]

        return ""

    @staticmethod
    def _append_request_id(detail: str, response: httpx.Response) -> str:
        request_id = (
            response.headers.get("request-id")
            or response.headers.get("x-request-id")
            or response.headers.get("xi-request-id")
        )
        if request_id:
            return f"{detail} (request_id: {request_id})"
        return detail
