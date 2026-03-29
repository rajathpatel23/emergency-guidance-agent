import os
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from log_config import setup_logging
from pipeline import create_pipeline
from session_manager import create_session, get_session, end_session, all_sessions

load_dotenv()
setup_logging(level=os.getenv("LOG_LEVEL", "DEBUG"))

app = FastAPI(title="CPR Copilot API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/session")
async def new_session():
    session = create_session()
    return session.to_dict()

@app.get("/session/{session_id}")
async def fetch_session(session_id: str):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.to_dict()

@app.get("/debug/sessions")
async def debug_sessions():
    """Live view of all in-memory sessions."""
    sessions = all_sessions()
    return {"count": len(sessions), "sessions": sessions}

@app.websocket("/ws/stream/{session_id}")
async def stream(websocket: WebSocket, session_id: str):
    session = get_session(session_id)
    if not session:
        logger.warning(f"[ws] rejected — session {session_id[:8]} not found")
        await websocket.close(code=4004, reason="Session not found")
        return

    await websocket.accept()
    logger.info(f"[ws] connected  session={session_id[:8]}  step={session.current_step}")

    try:
        logger.info(f"[ws] building pipeline for session={session_id[:8]}")
        runner, task = await create_pipeline(websocket, session)
        logger.info(f"[ws] pipeline ready — starting runner")
        await runner.run(task)
    except Exception:
        logger.exception("[ws] pipeline error")
    finally:
        logger.info(f"[ws] closed     session={session_id[:8]}  final_step={session.current_step}")
        end_session(session_id)
