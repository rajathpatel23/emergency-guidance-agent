import os

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from pipeline import create_pipeline
from session_manager import create_session, get_session, end_session

load_dotenv()

app = FastAPI(title="CPR Copilot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.websocket("/ws/stream/{session_id}")
async def stream(websocket: WebSocket, session_id: str):
    session = get_session(session_id)
    if not session:
        await websocket.close(code=4004, reason="Session not found")
        return

    await websocket.accept()

    try:
        runner, task = await create_pipeline(websocket, session)
        await runner.run(task)
    except Exception:
        import traceback
        traceback.print_exc()
    finally:
        end_session(session_id)
