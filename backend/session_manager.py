import uuid
from loguru import logger
from models import SessionState

_store: dict[str, SessionState] = {}

def create_session() -> SessionState:
    session_id = str(uuid.uuid4())
    session = SessionState(session_id=session_id)
    _store[session_id] = session
    logger.info(f"[session] created  id={session_id[:8]}  active={len(_store)}")
    return session

def get_session(session_id: str):
    return _store.get(session_id)

def update_session(session_id: str, **kwargs):
    session = _store.get(session_id)
    if not session:
        logger.warning(f"[session] update failed — {session_id[:8]} not found")
        return None
    for key, value in kwargs.items():
        if hasattr(session, key):
            setattr(session, key, value)
    if "current_step" in kwargs:
        logger.debug(f"[session] updated  id={session_id[:8]}  step={session.current_step}  attempts={session.step_attempts}")
    return session

def end_session(session_id: str) -> None:
    session = _store.get(session_id)
    if session:
        session.status = "ended"
        logger.info(f"[session] ended    id={session_id[:8]}  final_step={session.current_step}")

def all_sessions() -> list[dict]:
    return [s.to_dict() for s in _store.values()]
