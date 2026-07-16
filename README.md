# portfolio-ai-api

A voice-enabled FastAPI backend that powers Rebecca Drennan's AI Portfolio Assistant.

This repository provides the API layer for a portfolio experience where visitors can explore Rebecca's background through chat, speech-to-text input, and text-to-speech playback. The assistant combines Google Gemini for grounded responses with ElevenLabs for voice features, all backed by a curated markdown knowledge base and backend-only secret handling.

## Highlights

- Chat API powered by Google Gemini and portfolio-specific context
- Speech-to-text transcription via ElevenLabs `scribe_v2`
- Text-to-speech playback via a backend-only ElevenLabs proxy
- Public-safe markdown knowledge base with contact-detail redaction
- FastAPI validation, typed request models, and endpoint tests

## Demo

Swagger UI walkthrough (health check + chat request):

![Swagger UI Demo](docs/assets/SwaggerUI.gif)

## What This Project Powers

This backend powers Rebecca's AI Portfolio Assistant by:

- receiving portfolio questions from a frontend chat interface,
- turning recorded microphone input into text through ElevenLabs speech-to-text,
- generating natural-sounding spoken replies through ElevenLabs text-to-speech,
- loading portfolio context from structured markdown files,
- redacting sensitive contact details before sending context to the model,
- returning concise, grounded, professional responses.

## Core Capabilities

- Grounded chat responses sourced from local portfolio content rather than open-ended model recall
- Voice-ready API surface for modern frontend experiences
- Backend-only secret management so third-party API keys never reach the browser
- Clean separation between app models, prompt logic, and external service integrations
- Test coverage for the voice endpoint contract and ElevenLabs service behavior

## Tech Stack

- Python 3.11+
- FastAPI
- Uvicorn
- Google Gemini API (`google-genai`)
- ElevenLabs speech-to-text and text-to-speech APIs
- Pydantic
- python-dotenv
- httpx
- python-multipart
- pypdf
- pytest
- CORS middleware

## Project Structure

```text
portfolio-ai-api/
  .github/
    ISSUE_TEMPLATE/
      bug_report.md
      feature_request.md
      config.yml
    pull_request_template.md
    workflows/
      ci.yml
  app/
    __init__.py
    main.py
    models/
      __init__.py
      chat.py
      voice.py
    services/
      __init__.py
      elevenlabs_service.py
      gemini_service.py
      knowledge_service.py
    prompts/
      __init__.py
      system_prompt.py
    data/
      about.md
      certifications.md
      conferences.md
      education.md
      experience.md
      faq.md
      skills.md
      projects/
        ai-portfolio-assistant.md
        binder.md
        serve-youth.md
  tests/
    __init__.py
    test_imports.py
    test_voice_endpoints.py
  docs/
    assets/
  .env.example
  .gitignore
  .editorconfig
  CODE_OF_CONDUCT.md
  CONTRIBUTING.md
  LICENSE
  pyproject.toml
  requirements.txt
  README.md
  SECURITY.md
```

## Quality and CI

- A GitHub Actions workflow runs automated checks on every push and pull request to `main`.
- Voice endpoint behavior is covered by focused API and service-level tests.
- Local test command:

```bash
python -m pytest -q
```

- Contributor guidelines are in `CONTRIBUTING.md`.

## Voice Architecture

Text diagram:

```text
Browser chat UI
  -> POST /speech-to-text (multipart audio)
    -> FastAPI validation and size checks
      -> ElevenLabs Speech-to-Text (scribe_v2)
  -> transcript returned to frontend chat thread
  -> POST /chat (existing JSON message flow)
    -> FastAPI + Gemini + portfolio knowledge base
  -> assistant text returned to frontend chat thread
  -> POST /text-to-speech (assistant reply JSON)
    -> FastAPI validation
      -> ElevenLabs Text-to-Speech stream endpoint
  -> backend proxies audio bytes back to browser for playback
```

Security boundary:

- The frontend must never call ElevenLabs directly.
- `ELEVENLABS_API_KEY` stays in backend-only environment configuration.
- The backend proxies both speech-to-text and text-to-speech so the browser never sees the ElevenLabs key or a third-party URL.

## Why The Voice Layer Matters

The voice endpoints make the portfolio assistant feel like a product rather than a static chatbot demo. Visitors can speak naturally, receive spoken responses, and explore Rebecca's work through a more accessible interface while the backend keeps vendor credentials and request orchestration private.

## Repository Standards

- License: MIT in `LICENSE`.
- Code of conduct: `CODE_OF_CONDUCT.md`.
- Security disclosure guidance: `SECURITY.md`.
- Issue templates: `.github/ISSUE_TEMPLATE/`.
- Pull request template: `.github/pull_request_template.md`.
- Editor consistency settings: `.editorconfig`.

## Local Setup

1. Create and activate a virtual environment.

Windows Command Prompt (`cmd`):

```bat
py -m venv .venv
.venv\Scripts\activate.bat
```

Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

3. Create your environment file from the example:

```bash
copy .env.example .env
```

4. Add your Gemini and ElevenLabs settings in `.env`:

```env
GEMINI_API_KEY=your_real_api_key_here
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
ELEVENLABS_VOICE_ID=your_elevenlabs_voice_id_here
ELEVENLABS_TTS_MODEL_ID=your_preferred_tts_model_id_here
```

If `ELEVENLABS_TTS_MODEL_ID` is left empty, the backend defaults to `eleven_multilingual_v2`.

## Getting a Gemini API Key

1. Go to Google AI Studio.
2. Create or sign in to your Google account.
3. Generate an API key.
4. Paste it into `.env` as `GEMINI_API_KEY`.

Never commit your real API key. This repository ignores `.env` by default.

## Getting an ElevenLabs API Key and Voice ID

1. Sign in to ElevenLabs.
2. Create an API key in the ElevenLabs dashboard.
3. Copy the key into `.env` as `ELEVENLABS_API_KEY`.
4. Select a voice from your ElevenLabs voice library and copy its voice ID into `ELEVENLABS_VOICE_ID`.
5. Optionally set `ELEVENLABS_TTS_MODEL_ID` if you want to override the backend default.

Warning:

- Never expose the ElevenLabs API key in frontend code, browser requests, or `VITE_` variables.
- Keep the key only in the FastAPI backend environment.

## Knowledge Base

Production knowledge source:

- Markdown files in `app/data/` (including nested folders) are the primary public production knowledge base.

Optional local development source:

- `app/data/LinkedinExport.pdf` can be used locally as an additional context source.
- `app/data/LinkedinExport.pdf` is gitignored and should not be committed.

How to extend knowledge safely:

- Add new knowledge by creating additional `.md` files in `app/data/`.
- The assistant only answers from the loaded context.
- Never add sensitive or private details to public markdown files.
- Never include confidential employer, client, or internal project details.

Important:

- The backend does not scrape LinkedIn.
- Any LinkedIn export PDF must be provided manually for local use only.

## How Knowledge Extraction Works

`knowledge_service.py`:

- recursively reads all `.md` files in `app/data/` and treats them as the main source,
- optionally reads `app/data/LinkedinExport.pdf` with `pypdf` for local development,
- combines loaded content into a single context string,
- includes each markdown file name as a heading before its content,
- gracefully handles missing/unreadable files (no crash),
- redacts sensitive contact details before context is sent to Gemini.

## Sensitive Data Protection

Before sending context to Gemini, the backend redacts:

- email addresses,
- UK mobile-style phone numbers,
- likely home address lines (including postcode/address-like patterns).

This helps reduce accidental exposure of private contact details in responses.

## Run the API

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API will be available at:

- `http://localhost:8000`
- Docs: `http://localhost:8000/docs`

For local microphone testing, serve your frontend from `http://localhost` during development. Most modern browsers allow microphone access on localhost, but permission prompts, autoplay policy, and codec support still vary by browser.

## Endpoints

### GET /health

Response:

```json
{
  "status": "ok",
  "service": "portfolio-ai-api"
}
```

### POST /chat

Request:

```json
{
  "message": "Tell me about Rebecca's React experience"
}
```

Response:

```json
{
  "reply": "..."
}
```

Example cURL:

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"message":"Tell me about Rebecca\'s React experience"}'
```

### POST /speech-to-text

Accepts multipart form-data with an `audio` file field.

Supported content types:

- `audio/webm`
- `audio/ogg`
- `audio/mp4`
- `audio/wav`

Notes:

- Uploads are limited to 10 MB.
- The backend forwards audio to ElevenLabs using the current `scribe_v2` speech-to-text model.
- The backend returns a small typed JSON payload.

Response:

```json
{
  "text": "transcribed question"
}
```

Example cURL:

```bash
curl -X POST "http://localhost:8000/speech-to-text" \
  -F "audio=@sample.webm;type=audio/webm"
```

### POST /text-to-speech

Accepts JSON:

```json
{
  "text": "assistant response"
}
```

Notes:

- Empty text is rejected.
- Text is limited to 4000 characters.
- The backend calls the ElevenLabs streaming text-to-speech endpoint using `ELEVENLABS_VOICE_ID`.
- Audio is proxied back from FastAPI to the browser with the upstream audio content type.

Example cURL:

```bash
curl -X POST "http://localhost:8000/text-to-speech" \
  -H "Content-Type: application/json" \
  --output reply.mp3 \
  -d '{"text":"Hello from Rebecca\'s portfolio assistant"}'
```

## Connect to a React Frontend

Your React app can call this API from `http://localhost:5173` or `http://localhost:3000` (both are enabled in CORS).

Typical frontend flow:

1. collect user input from chat UI,
2. `POST` to `/chat` with `{ "message": "..." }`,
3. display `reply` in the conversation thread.

Voice-enabled frontend flow:

1. record microphone audio in the browser with `MediaRecorder`,
2. `POST` the recorded blob to `/speech-to-text` as multipart form-data with the `audio` field,
3. insert the returned `text` into the existing chat flow as the user's message,
4. `POST` that transcript to the existing `/chat` endpoint,
5. display the returned `reply` normally in the chat UI,
6. if voice replies are enabled, `POST` `{ "text": reply }` to `/text-to-speech`,
7. play the returned audio blob in the browser.

Recommended frontend service helpers:

- `transcribeAudio(blob: Blob): Promise<{ text: string }>`
- `sendChatMessage(message: string): Promise<{ reply: string }>`
- `generateSpeech(text: string): Promise<Blob>`

## Professional Focus

This repository is intended to showcase practical backend engineering for AI products: API design, service abstraction, prompt safety, knowledge grounding, secret isolation, and production-aware voice integration. It is a portfolio project, but it is structured to read like a maintainable application rather than a one-off demo.

Suggested request shapes from React:

```ts
export async function transcribeAudio(blob: Blob): Promise<{ text: string }> {
  const formData = new FormData();
  formData.append("audio", blob, "recording.webm");

  const response = await fetch("http://localhost:8000/speech-to-text", {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error("Transcription failed");
  }

  return response.json();
}

export async function generateSpeech(text: string): Promise<Blob> {
  const response = await fetch("http://localhost:8000/text-to-speech", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });

  if (!response.ok) {
    throw new Error("Speech generation failed");
  }

  return response.blob();
}
```

Browser limitations to account for in the frontend:

- microphone permission must be requested from a user gesture,
- autoplay may block audio playback until the user has interacted with the page,
- `MediaRecorder` MIME support differs by browser, so prefer checking supported types before recording,
- iOS Safari may have stricter recording and autoplay behavior than desktop Chrome.

## Run Tests

```bash
python -m pytest -q
```

Current tests validate that:

- FastAPI app imports correctly,
- knowledge service imports correctly,
- Gemini service imports correctly,
- `/speech-to-text` validates missing files and unsupported MIME types,
- `/speech-to-text` returns transcripts when ElevenLabs succeeds,
- `/text-to-speech` validates empty and oversized input,
- `/text-to-speech` proxies audio bytes back to the client,
- ElevenLabs timeout, upstream error, and missing configuration paths are handled.

Useful local verification commands:

```bash
python -m pytest -q
python -m pytest tests/test_voice_endpoints.py -q
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
