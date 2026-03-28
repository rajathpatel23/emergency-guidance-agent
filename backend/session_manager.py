import uuid
from models import SessionState


_store: dict[str, SessionState] = {}


def create_session() -> SessionState:
    session_id = str(uuid.uuid4())
    session = SessionState(session_id=session_id)
    _store[session_id] = session
    return session


def get_session(session_id: str):
    return _store.get(session_id)


def update_session(session_id: str, **kwargs):
    session = _store.get(session_id)
    if not session:
        return None
    for key, value in kwargs.items():
        if hasattr(session, key):
            setattr(session, key, value)
    return session


def end_session(session_id: str) -> None:
    session = _store.get(session_id)
    if session:
        session.status = "ended"
