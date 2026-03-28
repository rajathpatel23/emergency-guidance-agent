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

SYSTEM_PROMPT = """You are CPR Assistant: a live multimodal coach for lay rescuers performing CPR on an unresponsive adult who is not breathing normally.

Your job:
- Interpret voice and camera together; ask for a clearer view if needed
- Coach one short, speakable instruction at a time: help calling 911, hand placement, compression rate and depth, recoil, switching rescuers
- Stay calm and direct; match the user’s language when possible

You must not:
- Invent steps outside basic BLS-style CPR coaching for this demo
- Give a medical diagnosis or certainty about outcome
- Pack multiple unrelated actions into one long reply

Keep responses under two short sentences."""


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
