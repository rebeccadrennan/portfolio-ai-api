from pydantic import BaseModel


class SpeechToTextResponse(BaseModel):
    text: str


class TextToSpeechRequest(BaseModel):
    text: str
