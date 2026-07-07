from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.models.chat import ChatRequest, ChatResponse
from app.services.gemini_service import GeminiService, GeminiServiceError

app = FastAPI(title="Rebecca Drennan Portfolio AI API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://www.rebeccadrennan.co.uk",
        "https://rebeccadrennan.co.uk",
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

chat_service = GeminiService()


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
