from __future__ import annotations

import os

from dotenv import load_dotenv
from google import genai

from app.prompts.system_prompt import SYSTEM_PROMPT
from app.services.knowledge_service import get_portfolio_context

load_dotenv()


class GeminiServiceError(RuntimeError):
    """Raised when the Gemini service cannot produce a safe, valid response."""


class GeminiService:
    def __init__(self, api_key: str | None = None, model: str = "gemini-2.5-flash") -> None:
        self.api_key = (api_key or os.getenv("GEMINI_API_KEY", "")).strip()
        self.model = model
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None

    def generate_reply(self, user_question: str) -> str:
        cleaned_question = user_question.strip()
        if not cleaned_question:
            raise GeminiServiceError("Cannot process an empty question.")

        if not self.api_key:
            raise GeminiServiceError(
                "GEMINI_API_KEY is missing. Add it to your .env file before calling /chat."
            )

        if self.client is None:
            raise GeminiServiceError("Gemini client could not be initialized.")

        prompt = self._build_prompt(cleaned_question)

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
            )
        except Exception as exc:
            raise GeminiServiceError(f"Gemini API request failed: {exc}") from exc

        reply = self._extract_text(response)
        if not reply:
            raise GeminiServiceError("Gemini returned an empty or invalid response.")

        return reply

    def _build_prompt(self, user_question: str) -> str:
        portfolio_context = get_portfolio_context()
        return (
            f"System Instructions:\n{SYSTEM_PROMPT}\n\n"
            f"Portfolio Context:\n{portfolio_context}\n\n"
            f"User Question:\n{user_question}\n\n"
            "Assistant Response:"
        )

    @staticmethod
    def _extract_text(response: object) -> str:
        direct_text = getattr(response, "text", None)
        if isinstance(direct_text, str) and direct_text.strip():
            return direct_text.strip()

        candidates = getattr(response, "candidates", None) or []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            parts = getattr(content, "parts", None) or []
            for part in parts:
                part_text = getattr(part, "text", None)
                if isinstance(part_text, str) and part_text.strip():
                    return part_text.strip()

        return ""
