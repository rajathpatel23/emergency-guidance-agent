# CPR Copilot — API reference (Python backend)

This document describes the **primary realtime API**: FastAPI in `backend/` (`uvicorn main:app`). It powers **CPR Copilot** (voice + optional camera) via **Pipecat** and **Gemini Live**.

A separate **Node/Fastify** app in `apps/api` exists for **stub** workflow testing with simple JSON over WebSocket; it is optional and not required for the browser demo.

**Base URL (local):** `http://localhost:8000`  
**WebSocket base:** `ws://localhost:8000`

---

## HTTP

### `GET /health`

Liveness check.

**Response**

```json
{"status": "ok"}
```

---

### `POST /session`

Creates an in-memory session. Call this **before** opening the WebSocket.

**Response** — `SessionState` as JSON (same fields as `GET /session/{session_id}`):

```json
{
  "session_id": "3f8a1b2c-…",
  "scenario": "cpr_coaching",
  "language": "en",
  "current_step": "intake",
  "called_emergency": false,
  "view_quality": "unknown",
  "patient_visible": false,
  "compressions_detected": "unknown",
  "last_instruction": "",
  "step_attempts": 0,
  "status": "active"
}
```

---

### `GET /session/{session_id}`

Returns the current session snapshot (debug / reconnect).

**404** if the session id is unknown or expired.

---

### `GET /debug/sessions`

Returns all in-memory sessions (development only).

```json
{
  "count": 1,
  "sessions": [ { "...": "..." } ]
}
```

---

## Session state (`SessionState`)

| Field | Type | Description |
|--------|------|-------------|
| `session_id` | string | UUID |
| `scenario` | string | `"cpr_coaching"` |
| `language` | string | Language code (e.g. `"en"`) |
| `current_step` | string | Workflow step id (see table below) |
| `called_emergency` | bool | Reserved / future use |
| `view_quality` | string | `"unknown"` \| `"clear"` \| `"unclear"` |
| `patient_visible` | bool | Heuristic: patient / chest thought to be visible |
| `compressions_detected` | string | `"unknown"` \| `"yes"` \| `"no"` |
| `last_instruction` | string | Last instruction string (if set server-side) |
| `step_attempts` | int | Attempts / repeats within the current step |
| `status` | string | `"active"` \| `"ended"` |

Source of truth in code: `backend/models.py` (`SessionState.to_dict()`).

---

## Workflow steps (CPR coaching)

| Step | # | Label (human) |
|------|---|----------------|
| `intake` | 1 | Intake |
| `escalation` | 2 | Escalation |
| `see_patient` | 3 | See patient |
| `start_compressions` | 4 | Start compressions |
| `continue_cpr` | 5 | Continue CPR |
| `complete` | 6 | Complete |

The **app-owned** state machine is `backend/workflow_engine.py` (`evaluate` / `apply_decision`). Gemini suggests wording; **code** decides allowed transitions.

---

## WebSocket — `WS /ws/stream/{session_id}`

After `POST /session`, connect to:

`ws://localhost:8000/ws/stream/{session_id}`

### What the browser actually uses (CPR Copilot)

The React app (`cpr-copilot`) uses **Pipecat**:

- **Transport:** `@pipecat-ai/websocket-transport` with a **protobuf** frame serializer (matches `FastAPIWebsocketTransport` + `ProtobufFrameSerializer` on the server).
- **Audio:** microphone audio is streamed as Pipecat frames (**16 kHz** mono PCM in, **24 kHz** PCM out for model output — see `useGuidanceSession` and `pipeline.py`).
- **Video:** the client periodically sends **JPEG** frames as **separate raw messages** (not the old “all JSON” protocol), e.g. `{ "type": "frame", "data": "<base64 JPEG>" }` at ~1 fps. Ingestion may still be wired through the Pipecat/Gemini path depending on deployment.
- **Text:** the Pipecat client surfaces **bot** text via events such as `botOutput` / `botTranscript`, and **user** text via `userTranscript`. There is no guarantee that the server emits a JSON envelope like `{ "type": "instruction", ... }` for every turn—**the live path is Pipecat + Gemini Live**, not a custom REST-style JSON stream.

So: **do not assume** the WebSocket speaks only plain JSON for the primary demo. Treat the **Pipecat + protobuf** contract as authoritative for audio; treat HTTP `SessionState` as authoritative for **workflow step** after refreshes.

### Optional client hooks

The frontend may listen for **`serverMessage`** payloads (e.g. `type: "state_update"`). If present, they can drive UI progress; **not all builds** emit these from the Python pipeline yet—always verify against the running client.

---

## Optional Node API (`apps/api`)

For protocol experiments without Python/Pipecat:

- Default port **3001** (`PORT` env).
- **HTTP:** `POST /session`, `GET /health`.
- **WebSocket:** `GET /ws/:sessionId` — **JSON**-oriented stub (see `apps/api/src/index.ts`), **not** the same binary protocol as the Pipecat client.

Use this only to exercise shared types and the stub `GeminiOrchestrator`.

---

## Running the Python API locally

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# From repo root (same as README): template → `.env`, then set GEMINI_API_KEY
cp ../.env.example ../.env

uvicorn main:app --reload --port 8000
```

Interactive HTTP docs: `http://localhost:8000/docs`

---

## Implementation notes

- **Gemini Live** is opened inside the Pipecat pipeline in `backend/pipeline.py` (`GeminiLiveLLMService`). Response modalities (e.g. text vs audio) are configured there, not via a separate “gemini session” module.
- **Model → workflow:** `WorkflowProcessor` runs after model turns; `ModelInterpretation` is built with **heuristics** on model/user text (`_extract_interpretation` in `pipeline.py`). This can later be replaced with structured JSON from the model.
- **Visibility / trust:** `user_asserts_view_adequate` and `person_visible` feed `workflow_engine.evaluate` for the `see_patient` step (see `backend/workflow_engine.py` and `backend/prompts.py`).
