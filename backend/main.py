import asyncio
import base64
import json
import os

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from gemini_session import open_gemini_session
from models import ModelInterpretation, SessionState
from session_manager import create_session, get_session, update_session, end_session
from workflow_engine import evaluate, apply_decision, current_config, step_number, TOTAL_STEPS
from prompts import build_system_prompt, step_context_message

load_dotenv()

app = FastAPI(title="Emergency Guidance Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/session")
async def new_session():
    """Create a new guidance session. Returns session_id and initial state."""
    session = create_session()
    return session.to_dict()


@app.get("/session/{session_id}")
async def fetch_session(session_id: str):
    """Fetch current state of an existing session."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.to_dict()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_interpretation(text: str, transcript: str = "") -> ModelInterpretation:
    """
    Heuristic extraction of model signals from Gemini's response text.
    Replace with structured JSON output once Gemini supports it reliably.
    """
    combined = (text + " " + transcript).lower()
    return ModelInterpretation(
        injury_visible=any(w in combined for w in ["blood", "bleed", "wound", "cut", "injury", "arm", "laceration"]),
        view_unclear=any(w in combined for w in ["cannot see", "can't see", "unclear", "move the camera", "closer", "better angle", "show me"]),
        pressure_applied=any(w in combined for w in ["pressing", "pressure", "holding", "firm", "pushing"]),
        transcript_summary=transcript,
    )


def _build_response(session: SessionState, instruction: str, uncertain: bool = False) -> dict:
    config = current_config(session)
    return {
        "type": "instruction",
        "session_id": session.session_id,
        "current_step": session.current_step,
        "step_label": config.label,
        "step_number": step_number(session.current_step),
        "total_steps": TOTAL_STEPS,
        "instruction": instruction or config.default_instruction,
        "uncertain": uncertain,
        "speak": True,
        "language": session.language,
    }


# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------

@app.websocket("/ws/stream/{session_id}")
async def stream(websocket: WebSocket, session_id: str):
    """
    Full-duplex live guidance session scoped to a session_id.

    Client → server message shapes:
      {"type": "frame",      "data": "<base64 JPEG>"}
      {"type": "audio",      "data": "<base64 PCM 16kHz mono s16le>"}
      {"type": "transcript", "text": "<user speech>"}
      {"type": "user.done"}
      {"type": "user.repeat"}
      {"type": "end"}

    Server → client message shapes:
      {"type": "status",      "status": "connected", ...session fields}
      {"type": "instruction", "current_step": "...", "instruction": "...", ...}
      {"type": "state_update","current_step": "...", ...session fields}
      {"type": "error",       "message": "..."}
    """
    session = get_session(session_id)
    if not session:
        await websocket.close(code=4004, reason="Session not found")
        return

    await websocket.accept()

    system_prompt = build_system_prompt(session.current_step)

    try:
        async with open_gemini_session(system_prompt) as gemini:

            await websocket.send_json({
                "type": "status",
                "status": "connected",
                **session.to_dict(),
            })

            # Accumulate text chunks per Gemini turn
            accumulated_text: list[str] = []
            last_transcript: str = ""

            async def receive_from_client():
                nonlocal last_transcript
                try:
                    while True:
                        raw = await websocket.receive_text()
                        msg = json.loads(raw)

                        match msg.get("type"):
                            case "frame":
                                frame_bytes = base64.b64decode(msg["data"])
                                await gemini.send_frame(frame_bytes)

                            case "audio":
                                audio_bytes = base64.b64decode(msg["data"])
                                await gemini.send_audio(audio_bytes)

                            case "transcript":
                                last_transcript = msg.get("text", "")
                                await gemini.send_text(last_transcript)

                            case "user.done":
                                _handle_user_action(session, "done")

                            case "user.repeat":
                                _handle_user_action(session, "repeat")

                            case "end":
                                end_session(session_id)
                                return

                except WebSocketDisconnect:
                    pass

            async def receive_from_gemini():
                nonlocal last_transcript
                async for response in gemini.responses():

                    if response["type"] == "text":
                        chunk = response["content"]
                        accumulated_text.append(chunk)
                        # Forward chunk immediately so UI can stream
                        await websocket.send_json({"type": "text_chunk", "content": chunk})

                    elif response["type"] == "audio":
                        await websocket.send_json(response)

                    elif response["type"] == "turn_complete":
                        full_text = "".join(accumulated_text).strip()
                        accumulated_text.clear()

                        if not full_text:
                            continue

                        # Extract interpretation from what Gemini said + user transcript
                        interp = _extract_interpretation(full_text, last_transcript)
                        last_transcript = ""

                        # Workflow engine decides next step
                        decision = evaluate(session, interp, user_action=None)
                        prev_step = session.current_step
                        apply_decision(session, decision)
                        update_session(session_id,
                                       current_step=session.current_step,
                                       step_attempts=session.step_attempts,
                                       injury_visible=interp.injury_visible,
                                       view_quality="unclear" if interp.view_unclear else "clear",
                                       pressure_applied="yes" if interp.pressure_applied else session.pressure_applied,
                                       last_instruction=full_text)

                        # If step advanced, inject context into Gemini
                        if session.current_step != prev_step:
                            await gemini.send_text(step_context_message(session.current_step))
                            await websocket.send_json({
                                "type": "state_update",
                                **session.to_dict(),
                            })

                        await websocket.send_json(
                            _build_response(session, full_text, uncertain=interp.view_unclear)
                        )

            def _handle_user_action(session: SessionState, action: str):
                decision = evaluate(session, ModelInterpretation(), user_action=action)
                prev_step = session.current_step
                apply_decision(session, decision)
                update_session(session_id,
                               current_step=session.current_step,
                               step_attempts=session.step_attempts)

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
