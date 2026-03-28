import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from google import genai
from google.genai import types

MODEL = "gemini-2.0-flash-live-001"

SYSTEM_PROMPT = """You are a live multimodal guidance assistant for a bounded severe bleeding-control workflow.

Your job:
- Interpret the user's visible scene from the camera
- Determine whether the injury area is visible enough
- Determine whether the user appears to be applying pressure
- Produce one short, stress-friendly instruction at a time
- Ask for a clearer camera view if the scene is unclear
- Respond in the same language as the user when possible

You must not:
- Invent new protocols or steps
- Give broad medical diagnosis
- Provide long paragraphs
- Present more than one action at a time

Keep responses under 2 sentences. Be direct and calm."""


class GeminiLiveSession:
    def __init__(self, session):
        self._session = session

    async def send_frame(self, jpeg_bytes: bytes) -> None:
        """Forward a single JPEG frame to Gemini Live."""
        await self._session.send(
            input=types.LiveClientRealtimeInput(
                media_chunks=[types.Blob(data=jpeg_bytes, mime_type="image/jpeg")]
            )
        )

    async def send_audio(self, pcm_bytes: bytes) -> None:
        """Forward raw PCM audio (16kHz mono s16le) to Gemini Live."""
        await self._session.send(
            input=types.LiveClientRealtimeInput(
                media_chunks=[
                    types.Blob(data=pcm_bytes, mime_type="audio/pcm;rate=16000")
                ]
            )
        )

    async def send_text(self, text: str) -> None:
        """Send a text turn (e.g. user transcript) to Gemini Live."""
        await self._session.send(input=text, end_of_turn=True)

    async def responses(self) -> AsyncIterator[dict]:
        """Yield normalized response dicts from Gemini Live."""
        async for response in self._session.receive():
            if response.text:
                yield {"type": "text", "content": response.text}
            if response.data:
                # audio bytes — base64 encode before sending over WS
                import base64
                yield {"type": "audio", "data": base64.b64encode(response.data).decode()}
            if response.server_content and response.server_content.turn_complete:
                yield {"type": "turn_complete"}


@asynccontextmanager
async def open_gemini_session() -> AsyncIterator[GeminiLiveSession]:
    """Open a Gemini Live session for the duration of a WebSocket connection."""
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    config = types.LiveConnectConfig(
        response_modalities=["TEXT"],  # add "AUDIO" when ready for voice output
        system_instruction=SYSTEM_PROMPT,
    )
    async with client.aio.live.connect(model=MODEL, config=config) as session:
        yield GeminiLiveSession(session)
