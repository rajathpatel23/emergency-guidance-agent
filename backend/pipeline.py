# pipeline.py — Simplified audio-only pipeline
#
# Replaces the Pipecat + Gemini Live pipeline entirely.
# Flow:
#   1. Frontend sends JSON messages over WebSocket:
#      { "type": "transcript", "text": "..." }   <- user speech (STT done in browser)
#      { "type": "action", "action": "done"|"repeat" }  <- explicit user actions
#   2. Backend calls Claude (or any OpenAI-compatible LLM) with the transcript
#      and a prompt crafted to make the model guide CPR step-by-step.
#   3. Backend responds with JSON:
#      { "type": "instruction", "text": "...", "step": "...", "step_number": N, "total_steps": N }
#      { "type": "step_change", "from": "...", "to": "...", "step_number": N }
#      { "type": "error", "message": "..." }
#
# No Pipecat, no Gemini, no video frames, no Protobuf.

import json
import os

import anthropic
from fastapi import WebSocket
from loguru import logger

from models import ModelInterpretation, SessionState
from prompts import build_system_prompt, step_context_message
from session_manager import update_session
from workflow_engine import (
    TOTAL_STEPS,
    apply_decision,
    current_config,
    evaluate,
    step_number,
)

# ---------------------------------------------------------------------------
# LLM client (Anthropic Claude)
# ---------------------------------------------------------------------------

def _get_client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    return anthropic.Anthropic(api_key=api_key)


async def _call_llm(client: anthropic.Anthropic, session: SessionState, transcript: str) -> str:
    """
    Call Claude with the current CPR step context + user transcript.
    Returns the model's instruction text.
    """
    system_prompt = build_system_prompt(session.current_step)
    step_ctx = step_context_message(session.current_step)

    messages = [
        {
            "role": "user",
            "content": (
                f"{step_ctx}\n\n"
                f"The rescuer just said: \"{transcript}\"\n\n"
                "Based on what they said and the current CPR step, give them one short, calm instruction."
            ),
        }
    ]

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=200,
        system=system_prompt,
        messages=messages,
    )

    return response.content[0].text.strip()


# ---------------------------------------------------------------------------
# Heuristic interpretation from transcript (no video)
# ---------------------------------------------------------------------------

def _extract_interpretation(transcript: str) -> ModelInterpretation:
    """
    Infer CPR state signals from what the user says.
    These replace camera/vision signals — the model 'sees' through audio.
    """
    t = transcript.lower()
    return ModelInterpretation(
        person_visible=any(w in t for w in ["person", "patient", "him", "her", "them", "body", "lying", "on the floor", "unconscious"]),
        view_unclear=any(w in t for w in ["i don't know", "not sure", "what do i do", "help", "confused"]),
        hands_positioned=any(w in t for w in ["hands on", "placed my hands", "on the chest", "center of", "interlock"]),
        compressions_happening=any(w in t for w in ["pressing", "pushing", "compressing", "pumping", "doing compressions", "started", "going"]),
        person_responsive=any(w in t for w in ["responsive", "breathing", "moving", "awake", "conscious", "opened eyes", "coughing"]),
        transcript_summary=transcript,
    )


# ---------------------------------------------------------------------------
# WebSocket session handler — replaces create_pipeline()
# ---------------------------------------------------------------------------

async def handle_session(websocket: WebSocket, session: SessionState) -> None:
    """
    Main loop for one WebSocket connection.
    Receives transcript messages, calls LLM, drives workflow FSM, sends instructions back.
    """
    client = _get_client()
    conversation_history: list[dict] = []

    # Send initial greeting based on current step
    config = current_config(session)
    await _send(websocket, {
        "type": "instruction",
        "text": config.default_instruction,
        "step": session.current_step,
        "step_number": step_number(session.current_step),
        "total_steps": TOTAL_STEPS,
    })

    while True:
        try:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
        except Exception as e:
            logger.warning(f"[ws] receive error: {e}")
            break

        msg_type = msg.get("type")

        # --- User transcript (STT result from browser) ---
        if msg_type == "transcript":
            transcript = msg.get("text", "").strip()
            if not transcript:
                continue

            logger.debug(f"[ws] transcript: '{transcript}'")
            conversation_history.append({"role": "user", "content": transcript})

            prev_step = session.current_step

            # Infer CPR state from audio
            interp = _extract_interpretation(transcript)

            # Run workflow FSM
            decision = evaluate(session, interp, user_action=None)
            apply_decision(session, decision)

            update_session(
                session.session_id,
                current_step=session.current_step,
                step_attempts=session.step_attempts,
            )

            # Notify frontend if step changed
            if session.current_step != prev_step:
                logger.info(f"[workflow] {prev_step} → {session.current_step}")
                await _send(websocket, {
                    "type": "step_change",
                    "from": prev_step,
                    "to": session.current_step,
                    "step_number": step_number(session.current_step),
                    "total_steps": TOTAL_STEPS,
                })

            # Call LLM for the spoken instruction
            try:
                instruction = await _call_llm(client, session, transcript)
            except Exception as e:
                logger.error(f"[llm] error: {e}")
                instruction = current_config(session).default_instruction

            logger.debug(f"[llm] instruction: '{instruction[:100]}'")
            conversation_history.append({"role": "assistant", "content": instruction})

            await _send(websocket, {
                "type": "instruction",
                "text": instruction,
                "step": session.current_step,
                "step_number": step_number(session.current_step),
                "total_steps": TOTAL_STEPS,
            })

        # --- Explicit user action (Done / Repeat buttons) ---
        elif msg_type == "action":
            action = msg.get("action")
            if action not in ("done", "repeat"):
                continue

            logger.debug(f"[ws] user action: {action}")
            prev_step = session.current_step

            interp = ModelInterpretation()  # no transcript context for button actions
            decision = evaluate(session, interp, user_action=action)
            apply_decision(session, decision)

            update_session(
                session.session_id,
                current_step=session.current_step,
                step_attempts=session.step_attempts,
            )

            if session.current_step != prev_step:
                await _send(websocket, {
                    "type": "step_change",
                    "from": prev_step,
                    "to": session.current_step,
                    "step_number": step_number(session.current_step),
                    "total_steps": TOTAL_STEPS,
                })

            config = current_config(session)
            await _send(websocket, {
                "type": "instruction",
                "text": config.default_instruction,
                "step": session.current_step,
                "step_number": step_number(session.current_step),
                "total_steps": TOTAL_STEPS,
            })

        else:
            logger.debug(f"[ws] unknown message type: {msg_type}")


async def _send(websocket: WebSocket, payload: dict) -> None:
    try:
        await websocket.send_text(json.dumps(payload))
    except Exception as e:
        logger.warning(f"[ws] send error: {e}")
