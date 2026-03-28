import asyncio
import base64
import json
import os

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from gemini_session import open_gemini_session

load_dotenv()

app = FastAPI(title="Emergency Guidance Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten for production
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.websocket("/ws/stream")
async def stream(websocket: WebSocket):
    """
    Single WebSocket endpoint for a live guidance session.

    Client → server message shapes:
      {"type": "frame",   "data": "<base64 JPEG>"}
      {"type": "audio",   "data": "<base64 PCM 16kHz mono s16le>"}
      {"type": "transcript", "text": "user speech as text"}
      {"type": "end"}

    Server → client message shapes:
      {"type": "text",         "content": "..."}
      {"type": "audio",        "data": "<base64 PCM>"}
      {"type": "turn_complete"}
      {"type": "status",       "status": "connected"}
      {"type": "error",        "message": "..."}
    """
    await websocket.accept()

    try:
        async with open_gemini_session() as session:
            await websocket.send_json({"type": "status", "status": "connected"})

            async def receive_from_client():
                """Read frames/audio from the browser and forward to Gemini."""
                try:
                    while True:
                        raw = await websocket.receive_text()
                        msg = json.loads(raw)

                        match msg.get("type"):
                            case "frame":
                                frame_bytes = base64.b64decode(msg["data"])
                                await session.send_frame(frame_bytes)
                            case "audio":
                                audio_bytes = base64.b64decode(msg["data"])
                                await session.send_audio(audio_bytes)
                            case "transcript":
                                await session.send_text(msg.get("text", ""))
                            case "end":
                                return
                except WebSocketDisconnect:
                    pass

            async def receive_from_gemini():
                """Stream Gemini responses back to the browser."""
                async for response in session.responses():
                    try:
                        await websocket.send_json(response)
                    except WebSocketDisconnect:
                        return

            await asyncio.gather(receive_from_client(), receive_from_gemini())

    except Exception as exc:
        try:
            await websocket.send_json({"type": "error", "message": str(exc)})
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
