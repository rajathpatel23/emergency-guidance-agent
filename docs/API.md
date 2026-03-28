# Emergency Guidance Agent — API Reference

Base URL (local): `http://localhost:8000`
WebSocket base: `ws://localhost:8000`

---

## HTTP Endpoints

### `GET /health`

Liveness check.

**Response**
```json
{"status": "ok"}
```

---

## WebSocket Endpoints

### `WS /ws/stream`

Full-duplex live guidance session. Open one connection per user session.

**Connection lifecycle**
1. Client connects
2. Server sends `{"type": "status", "status": "connected"}`
3. Client streams frames and/or audio
4. Server streams Gemini responses
5. Client sends `{"type": "end"}` to close cleanly

---

### Client → Server messages

#### `frame`
A JPEG video frame captured from the camera.

```json
{
  "type": "frame",
  "data": "<base64-encoded JPEG>"
}
```

- Send at ~1 fps during an active session
- Resolution: 640×480 or lower recommended
- JPEG quality: 0.6–0.8 is sufficient

---

#### `audio`
Raw PCM audio from the microphone.

```json
{
  "type": "audio",
  "data": "<base64-encoded PCM>"
}
```

- Format: 16kHz, mono, signed 16-bit little-endian (s16le)
- Send in chunks as mic input is captured

---

#### `transcript`
User speech as text, or a text action from a button.

```json
{
  "type": "transcript",
  "text": "He cut his arm badly."
}
```

- Use when client-side STT is available
- Also used to relay button actions: `"I did it"`, `"Please repeat"`

---

#### `end`
Signals the client is done with the session.

```json
{
  "type": "end"
}
```

- Backend closes the Gemini Live session and the WebSocket

---

### Server → Client messages

#### `status`
Sent once when the session is ready.

```json
{
  "type": "status",
  "status": "connected"
}
```

---

#### `text`
A text instruction from Gemini. Display this prominently in the UI.

```json
{
  "type": "text",
  "content": "Press firmly on the wound with a clean cloth now."
}
```

- May arrive in chunks during streaming; concatenate until `turn_complete`

---

#### `audio`
Gemini spoken response as PCM audio (when audio modality is enabled).

```json
{
  "type": "audio",
  "data": "<base64-encoded PCM>"
}
```

- Format matches input: 16kHz mono s16le
- Decode and play via Web Audio API or `AudioContext`

---

#### `turn_complete`
Signals Gemini has finished its current response turn.

```json
{
  "type": "turn_complete"
}
```

- Use this to flip UI status back to `listening`
- Safe to render/speak the accumulated text at this point

---

#### `error`
A recoverable error. Show in UI and allow retry.

```json
{
  "type": "error",
  "message": "Gemini session failed to initialize."
}
```

---

## Planned Endpoints

These do not exist yet. They will be added when the workflow engine is integrated.

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/session` | Create a session, returns `session_id` |
| `GET` | `/session/{id}` | Fetch current session state |
| `WS` | `/ws/stream/{session_id}` | Scope stream to a named session |

---

## Running the backend locally

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp ../.env.example .env
# set GEMINI_API_KEY in .env

uvicorn main:app --reload --port 8000
```

FastAPI auto-generates interactive docs at `http://localhost:8000/docs` (HTTP endpoints only).

---

## Notes

- The Gemini Live session is opened per WebSocket connection and closed when the connection ends
- `response_modalities` is currently set to `["TEXT"]` — set to `["TEXT", "AUDIO"]` in `gemini_session.py` to enable voice output
- Frame rate and audio chunk size can be tuned; start at 1 fps for frames
