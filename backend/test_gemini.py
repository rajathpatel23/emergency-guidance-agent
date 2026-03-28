"""
Quick Gemini Live smoke test.
Sends a text prompt and saves the audio response to output.wav.

Usage:
    python test_gemini.py
Then open output.wav in any audio player.
"""

import asyncio
import os
import wave
import struct
from dotenv import load_dotenv
from google import genai
from google.genai.types import (
    HttpOptions,
    LiveConnectConfig,
    SpeechConfig,
    VoiceConfig,
    PrebuiltVoiceConfig,
    Content,
    Part,
)

load_dotenv()

MODEL = os.getenv(
    "GEMINI_LIVE_MODEL",
    "models/gemini-2.5-flash-native-audio-preview-12-2025",
)
PROMPT = "You are a CPR guidance assistant. Say hello and ask what is happening."
OUTPUT_FILE = "output.wav"
SAMPLE_RATE = 24000  # Gemini Live outputs 24kHz PCM


async def main():
    client = genai.Client(
        api_key=os.environ["GEMINI_API_KEY"],
        http_options=HttpOptions(api_version="v1alpha"),
    )

    config = LiveConnectConfig(
        response_modalities=["AUDIO"],
        system_instruction=Content(parts=[Part(text=PROMPT)]),
        speech_config=SpeechConfig(
            voice_config=VoiceConfig(
                prebuilt_voice_config=PrebuiltVoiceConfig(voice_name="Charon")
            )
        ),
    )

    print(f"Connecting to {MODEL}...")
    audio_chunks: list[bytes] = []

    async with client.aio.live.connect(model=MODEL, config=config) as session:
        print("Connected. Sending trigger...")
        await session.send_client_content(
            turns=[Content(role="user", parts=[Part(text="begin")])],
            turn_complete=True,
        )

        async for response in session.receive():
            if not hasattr(response, "server_content") or not response.server_content:
                continue
            sc = response.server_content
            if sc.model_turn:
                for part in sc.model_turn.parts:
                    if hasattr(part, "inline_data") and part.inline_data:
                        audio_chunks.append(part.inline_data.data)
            if getattr(sc, "turn_complete", False):
                break

    total = sum(len(c) for c in audio_chunks)
    print(f"Received {total} bytes of audio ({total / SAMPLE_RATE / 2:.1f}s)")

    # Write as 16-bit mono WAV
    with wave.open(OUTPUT_FILE, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(SAMPLE_RATE)
        for chunk in audio_chunks:
            wf.writeframes(chunk)

    print(f"Saved to {OUTPUT_FILE} — open it to hear Gemini speak.")


if __name__ == "__main__":
    asyncio.run(main())
