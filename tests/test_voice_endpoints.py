import asyncio

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app, voice_service
from app.services.elevenlabs_service import ElevenLabsService


client = TestClient(app)


class FakeAsyncClient:
    def __init__(
        self, *, response: httpx.Response | None = None, error: Exception | None = None
    ) -> None:
        self.response = response
        self.error = error
        self.calls: list[dict[str, object]] = []

    async def __aenter__(self) -> "FakeAsyncClient":
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> bool:
        return False

    async def post(self, path: str, **kwargs: object) -> httpx.Response:
        self.calls.append({"path": path, **kwargs})
        if self.error is not None:
            raise self.error
        assert self.response is not None
        return self.response


def test_speech_to_text_requires_audio_file() -> None:
    response = client.post("/speech-to-text")
    assert response.status_code == 400
    assert response.json() == {"detail": "Please attach an audio file in the 'audio' field."}


def test_speech_to_text_rejects_unsupported_audio_type() -> None:
    response = client.post(
        "/speech-to-text",
        files={"audio": ("recording.txt", b"not-audio", "text/plain")},
    )
    assert response.status_code == 415
    assert "Unsupported audio type" in response.json()["detail"]


def test_speech_to_text_returns_transcript_when_service_succeeds(monkeypatch: object) -> None:
    async def fake_transcribe_audio(**kwargs: object) -> str:
        assert kwargs["filename"] == "recording.webm"
        return "transcribed question"

    monkeypatch.setattr(voice_service, "transcribe_audio", fake_transcribe_audio)

    response = client.post(
        "/speech-to-text",
        files={"audio": ("recording.webm", b"audio-bytes", "audio/webm")},
    )

    assert response.status_code == 200
    assert response.json() == {"text": "transcribed question"}


def test_speech_to_text_without_api_key_returns_503(monkeypatch: object) -> None:
    original_api_key = voice_service.api_key
    monkeypatch.setattr(voice_service, "api_key", "")

    response = client.post(
        "/speech-to-text",
        files={"audio": ("recording.webm", b"audio-bytes", "audio/webm")},
    )

    monkeypatch.setattr(voice_service, "api_key", original_api_key)

    assert response.status_code == 503
    assert "ELEVENLABS_API_KEY is missing" in response.json()["detail"]


def test_text_to_speech_rejects_empty_text() -> None:
    response = client.post("/text-to-speech", json={"text": "   "})
    assert response.status_code == 400
    assert response.json() == {"detail": "Please provide non-empty text in the 'text' field."}


def test_text_to_speech_rejects_text_that_is_too_long() -> None:
    response = client.post("/text-to-speech", json={"text": "a" * 4001})
    assert response.status_code == 400
    assert "maximum length" in response.json()["detail"]


def test_text_to_speech_proxies_audio_when_service_succeeds(monkeypatch: object) -> None:
    async def fake_generate_speech_audio(text: str) -> tuple[bytes, str]:
        assert text == "Hello there"
        return b"audio-binary", "audio/mpeg"

    monkeypatch.setattr(voice_service, "generate_speech_audio", fake_generate_speech_audio)

    response = client.post("/text-to-speech", json={"text": "Hello there"})

    assert response.status_code == 200
    assert response.content == b"audio-binary"
    assert response.headers["content-type"].startswith("audio/mpeg")
    assert response.headers["cache-control"] == "no-store"


def test_service_transcribe_audio_calls_elevenlabs_and_returns_text() -> None:
    fake_client = FakeAsyncClient(
        response=httpx.Response(200, json={"text": "hello world"}),
    )
    service = ElevenLabsService(
        api_key="key",
        client_factory=lambda **kwargs: fake_client,
    )

    result = asyncio.run(
        service.transcribe_audio(
            filename="recording.webm",
            content_type="audio/webm",
            audio_bytes=b"audio-bytes",
        )
    )

    assert result == "hello world"
    assert fake_client.calls[0]["path"] == "/speech-to-text"


def test_service_generate_speech_audio_proxies_audio() -> None:
    fake_client = FakeAsyncClient(
        response=httpx.Response(200, content=b"mp3-bytes", headers={"content-type": "audio/mpeg"}),
    )
    service = ElevenLabsService(
        api_key="key",
        voice_id="voice-123",
        tts_model_id="eleven_turbo_v2_5",
        client_factory=lambda **kwargs: fake_client,
    )

    audio_bytes, media_type = asyncio.run(service.generate_speech_audio("Assistant reply"))

    assert audio_bytes == b"mp3-bytes"
    assert media_type == "audio/mpeg"
    assert fake_client.calls[0]["path"] == "/text-to-speech/voice-123/stream"


def test_service_maps_elevenlabs_timeout() -> None:
    fake_client = FakeAsyncClient(error=httpx.ReadTimeout("boom"))
    service = ElevenLabsService(
        api_key="key",
        client_factory=lambda **kwargs: fake_client,
    )

    with pytest.raises(Exception) as exc_info:
        asyncio.run(
            service.transcribe_audio(
                filename="recording.webm",
                content_type="audio/webm",
                audio_bytes=b"audio-bytes",
            )
        )

    assert "timed out" in str(exc_info.value)


def test_service_maps_elevenlabs_error_response() -> None:
    fake_client = FakeAsyncClient(
        response=httpx.Response(502, json={"detail": "upstream unavailable"}),
    )
    service = ElevenLabsService(
        api_key="key",
        voice_id="voice-123",
        client_factory=lambda **kwargs: fake_client,
    )

    with pytest.raises(Exception) as exc_info:
        asyncio.run(service.generate_speech_audio("Assistant reply"))

    assert "upstream unavailable" in str(exc_info.value)


def test_service_surfaces_nested_elevenlabs_error_reason_and_request_id() -> None:
    fake_client = FakeAsyncClient(
        response=httpx.Response(
            402,
            json={"detail": {"message": "voice is not available for this model"}},
            headers={"request-id": "req_123"},
        ),
    )
    service = ElevenLabsService(
        api_key="key",
        voice_id="voice-123",
        client_factory=lambda **kwargs: fake_client,
    )

    with pytest.raises(Exception) as exc_info:
        asyncio.run(service.generate_speech_audio("Assistant reply"))

    message = str(exc_info.value)
    assert "voice is not available for this model" in message
    assert "req_123" in message


def test_service_surfaces_plain_text_elevenlabs_error_reason() -> None:
    fake_client = FakeAsyncClient(
        response=httpx.Response(402, text="insufficient permissions for output format"),
    )
    service = ElevenLabsService(
        api_key="key",
        voice_id="voice-123",
        client_factory=lambda **kwargs: fake_client,
    )

    with pytest.raises(Exception) as exc_info:
        asyncio.run(service.generate_speech_audio("Assistant reply"))

    assert "insufficient permissions for output format" in str(exc_info.value)
