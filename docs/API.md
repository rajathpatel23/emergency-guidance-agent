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

### `POST /session`

Create a new guidance session. Call this before opening a WebSocket connection.

**Response** — initial `SessionState`
```json
{
  "session_id": "3f8a1b2c-...",
  "scenario": "bleeding_control",
  "language": "en",
  "current_step": "intake",
  "called_emergency": false,
  "view_quality": "unknown",
  "injury_visible": false,
  "pressure_applied": "unknown",
  "last_instruction": "",
  "step_attempts": 0,
  "status": "active"
}
```

---

### `GET /session/{session_id}`

Fetch current state of an existing session. Useful for the debug panel and reconnection.

**Response** — same shape as `POST /session`

**404** if session does not exist.

---

## WebSocket

### `WS /ws/stream/{session_id}`

Full-duplex live guidance session scoped to a `session_id`.

**Connection lifecycle**
1. `POST /session` → get `session_id`
2. `WS /ws/stream/{session_id}` → connect
3. Server sends `status: connected`
4. Client streams frames and/or audio
5. Server streams Gemini responses + workflow decisions
6. Client sends `end` to close cleanly

---

### Client → Server messages

#### `frame`
A JPEG video frame captured from the camera.

```json
{"type": "frame", "data": "<base64 JPEG>"}
```

- Send at ~1 fps during an active session
- JPEG quality: 0.6–0.8 recommended

---

#### `audio`
Raw PCM audio from the microphone.

```json
{"type": "audio", "data": "<base64 PCM>"}
```

- Format: 16kHz, mono, signed 16-bit little-endian (s16le)

---

#### `transcript`
User speech as text, or a button-triggered text action.

```json
{"type": "transcript", "text": "He cut his arm badly."}
```

---

#### `user.done`
User taps "I Did This". Triggers a `done` action in the workflow engine.

```json
{"type": "user.done"}
```

---

#### `user.repeat`
User taps "Repeat". Re-sends the current step instruction.

```json
{"type": "user.repeat"}
```

---

#### `end`
Ends the session cleanly.

```json
{"type": "end"}
```

---

### Server → Client messages

#### `status`
Sent once on connection. Includes full session state.

```json
{
  "type": "status",
  "status": "connected",
  "session_id": "...",
  "current_step": "intake",
  "step_label": "Intake",
  ...
}
```

---

#### `text_chunk`
Streaming text fragment from Gemini. Append to display buffer until `instruction` arrives.

```json
{"type": "text_chunk", "content": "Press firm"}
```

---

#### `instruction`
Full resolved instruction after a Gemini turn completes and the workflow engine has run. Use this to update the UI instruction panel.

```json
{
  "type": "instruction",
  "session_id": "...",
  "current_step": "apply_pressure",
  "step_label": "Apply Pressure",
  "step_number": 4,
  "total_steps": 6,
  "instruction": "Press firmly on the wound with a clean cloth now.",
  "uncertain": false,
  "speak": true,
  "language": "en"
}
```

- `step_number` / `total_steps` — drive the progress bar (1–6 of 6)
- `uncertain: true` — the scene is unclear; dim the instruction or add a warning
- `speak: true` — play this text via TTS

---

#### `state_update`
Sent when the workflow step advances. Contains full updated session state.

```json
{
  "type": "state_update",
  "session_id": "...",
  "current_step": "identify_injury",
  "step_label": "Identify Injury",
  "step_attempts": 0,
  ...
}
```

---

#### `audio`
Gemini spoken response as PCM (when audio modality is enabled).

```json
{"type": "audio", "data": "<base64 PCM>"}
```

---

#### `error`
A recoverable error. Show in UI and allow retry.

```json
{"type": "error", "message": "Gemini session failed to initialize."}
```

---

## Session state object

| Field | Type | Description |
|---|---|---|
| `session_id` | string | UUID |
| `scenario` | string | Always `"bleeding_control"` for MVP |
| `language` | string | Detected or configured language code |
| `current_step` | string | Active workflow step |
| `called_emergency` | bool | Whether user has been told to call emergency services |
| `view_quality` | string | `"unknown"` \| `"clear"` \| `"unclear"` |
| `injury_visible` | bool | Whether Gemini has indicated injury is visible |
| `pressure_applied` | string | `"unknown"` \| `"yes"` \| `"no"` |
| `last_instruction` | string | Last instruction sent to the user |
| `step_attempts` | int | How many times current step has been attempted |
| `status` | string | `"active"` \| `"ended"` |

---

## Workflow steps

| Step | Number | Label |
|---|---|---|
| `intake` | 1 | Intake |
| `escalation` | 2 | Escalation |
| `identify_injury` | 3 | Identify Injury |
| `apply_pressure` | 4 | Apply Pressure |
| `maintain_pressure` | 5 | Maintain Pressure |
| `complete` | 6 | Complete |

---

## Running locally

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp ../.env.example .env
# add GEMINI_API_KEY to .env

uvicorn main:app --reload --port 8000
```

FastAPI auto-generates interactive docs (HTTP only) at `http://localhost:8000/docs`.

---

## Notes

- The Gemini Live session opens on WS connect and closes on disconnect
- Voice output modality is configured on `GeminiLiveLLMService` in `backend/pipeline.py` (Pipecat), not in a separate session wrapper
- Model interpretation for the workflow is currently heuristic keyword matching over model/user text — can be replaced with structured JSON output from Gemini later
