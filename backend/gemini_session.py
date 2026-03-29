import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from google import genai
from google.genai import types

# Must be a model that supports the Live API (BidiGenerateContent). See pipeline.py / Pipecat defaults.
MODEL = os.getenv(
    "GEMINI_LIVE_MODEL",
    "models/gemini-2.5-flash-native-audio-preview-12-2025",
)

SYSTEM_PROMPT = """You are the Emergency Guidance Agent: a live multimodal coach for lay rescuers in emergencies (default: adult CPR when someone is unresponsive and not breathing normally).

Tone: urgent situations—be calm but extremely brief; no small talk. One short instruction or question per turn.

First time you speak: introduce yourself and ask what they need, e.g. "I'm the Emergency Guidance Agent. What can I help you with?"

Your job:
- Interpret voice and camera; ask for a clearer view if needed
- Coach: 911, hand placement, rate, depth, recoil, switching rescuers
- Match the user’s language when possible

You must not invent steps outside this demo scope or give a medical diagnosis.

Keep replies to two short sentences or less."""


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
                import base64

                yield {"type": "audio", "data": base64.b64encode(response.data).decode()}
            if response.server_content and response.server_content.turn_complete:
                yield {"type": "turn_complete"}


@asynccontextmanager
async def open_gemini_session(system_prompt: str = SYSTEM_PROMPT) -> AsyncIterator[GeminiLiveSession]:
    """Open a Gemini Live session for the duration of a WebSocket connection."""
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    config = types.LiveConnectConfig(
        response_modalities=["TEXT"],  # add "AUDIO" when ready for voice output
        system_instruction=system_prompt,
    )
    async with client.aio.live.connect(model=MODEL, config=config) as session:
        yield GeminiLiveSession(session)
