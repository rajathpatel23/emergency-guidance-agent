# Emergency Guidance Agent — Implementation Doc

## 1. Frontend Component Tree

```
App
└── SessionPage                      # single screen, owns WebSocket connection + session state
    ├── CameraPanel                  # camera permission, live preview
    │   └── VideoPreview             # <video> element bound to getUserMedia stream
    ├── InstructionPanel             # primary user-facing area
    │   ├── InstructionText          # large, prominent current instruction string
    │   └── StatusBadge              # enum: idle | listening | thinking | responding
    ├── TranscriptPanel              # scrollable log
    │   └── TranscriptEntry[]        # role: "system" | "user", text, timestamp
    ├── ActionBar                    # user controls
    │   ├── StartSessionButton       # visible only when session is idle
    │   ├── DoneButton               # "I Did This" — emits user.done
    │   ├── RepeatButton             # emits user.repeat
    │   └── EndSessionButton         # emits session.end
    ├── LanguageChip                 # displays session.language, e.g. "EN" | "ES"
    └── DebugPanel (dev only)        # collapsible
        ├── StateDisplay             # current_step, step_attempts, view_quality
        ├── LastInterpretation       # raw model interpretation fields
        └── EventLog                 # last N WebSocket events
```

### Component responsibilities

| Component | Owns | Does not own |
|---|---|---|
| SessionPage | WebSocket connection, session state object | Workflow logic |
| CameraPanel | MediaStream lifecycle, frame capture interval | Media encoding |
| InstructionPanel | Renders instruction + status | Decides what instruction to show |
| ActionBar | Emits user events to SessionPage | Handles responses |
| TranscriptPanel | Display only | Any state |

### Key frontend state (SessionPage)

```js
{
  sessionId: string | null,
  status: "idle" | "connecting" | "listening" | "thinking" | "responding" | "ended",
  currentStep: string,          // mirrors backend session.current_step
  currentInstruction: string,
  transcript: TranscriptEntry[],
  language: string,
  stream: MediaStream | null,   // camera+mic
  ws: WebSocket | null
}
```

---

## 2. Backend Module Structure

```
backend/
├── main.py                  # FastAPI app, HTTP routes, WebSocket endpoint, serves frontend
├── models.py                # Pydantic models: SessionState, ClientEvent, ServerEvent
├── session_manager.py       # SessionManager class — in-memory session store
├── workflow_engine.py       # WorkflowEngine class — FSM definition + transition logic
├── gemini_orchestrator.py   # GeminiOrchestrator class — Gemini Live session wrapper
├── response_formatter.py    # ResponseFormatter class — model output → UI payload
├── prompts.py               # System prompt templates per workflow state
└── config.py                # Env vars: GEMINI_API_KEY, MODEL_NAME, LOG_LEVEL
```

### Module responsibilities

**main.py**
- Mounts static frontend files
- `GET /` — serves index.html
- `GET /health` — liveness check
- `POST /session` — creates session, returns session_id
- `WebSocket /ws/{session_id}` — main real-time loop

**models.py**
```python
class SessionState(BaseModel):
    session_id: str
    scenario: str = "bleeding_control"
    language: str = "en"
    current_step: str = "intake"
    called_emergency: bool = False
    view_quality: str = "unknown"       # "unknown" | "clear" | "unclear"
    injury_visible: bool = False
    pressure_applied: str = "unknown"   # "unknown" | "yes" | "no"
    last_instruction: str = ""
    step_attempts: int = 0
    status: str = "active"              # "active" | "ended"

class ClientEvent(BaseModel):
    session_id: str
    event_type: str     # see event model in PRD §19
    transcript: str | None = None
    frame: str | None = None    # base64 JPEG
    audio: str | None = None    # base64 PCM

class ServerEvent(BaseModel):
    session_id: str
    event_type: str     # "assistant.instruction" | "assistant.status" | "assistant.error"
    current_step: str
    instruction: str | None = None
    speak: bool = False
    status: str = "responding"
    uncertain: bool = False
    language: str = "en"
    error: str | None = None

class ModelInterpretation(BaseModel):
    injury_visible: bool = False
    view_unclear: bool = False
    pressure_applied: bool = False
    suggested_instruction: str = ""
    language_detected: str = "en"
```

**session_manager.py**
```python
class SessionManager:
    # _sessions: dict[str, SessionState]

    def create(self) -> SessionState
    def get(self, session_id: str) -> SessionState | None
    def update(self, session_id: str, **kwargs) -> SessionState
    def end(self, session_id: str) -> None
```

**workflow_engine.py** — see §4 below

**gemini_orchestrator.py**
```python
class GeminiOrchestrator:
    async def open_session(self, system_prompt: str) -> GeminiSession
    async def send_audio(self, session, audio_bytes: bytes) -> None
    async def send_frame(self, session, jpeg_bytes: bytes) -> None
    async def send_text(self, session, text: str) -> None
    async def receive(self, session) -> AsyncIterator[ModelInterpretation | str]
    async def close_session(self, session) -> None
```

**response_formatter.py**
```python
class ResponseFormatter:
    def format(
        self,
        interpretation: ModelInterpretation,
        session: SessionState
    ) -> ServerEvent
```

**prompts.py**
```python
BASE_SYSTEM_PROMPT: str           # bounded workflow instructions
def build_state_prompt(step: str) -> str   # appends per-step objective
```

---

## 3. API Routes

### HTTP

| Method | Path | Request | Response | Purpose |
|---|---|---|---|---|
| GET | `/` | — | HTML | Serves frontend |
| GET | `/health` | — | `{"status": "ok"}` | Liveness |
| POST | `/session` | — | `{"session_id": "uuid"}` | Create session before WS connect |

### WebSocket: `/ws/{session_id}`

Connection lifecycle:
1. Client connects → backend confirms session exists or closes with 4004
2. Backend sends `session.started` with initial state
3. Client streams events; backend streams responses
4. Either side can initiate close

#### Client → Server events

| event_type | Required fields | Description |
|---|---|---|
| `session.start` | — | Signals camera/mic are ready |
| `media.frame` | `frame` (base64 JPEG) | Periodic video snapshot (~1fps) |
| `audio.chunk` | `audio` (base64 PCM 16kHz mono) | Continuous audio |
| `speech.transcript` | `transcript` | STT result if using client-side STT |
| `user.done` | — | User confirms step complete |
| `user.repeat` | — | User requests repeat of current instruction |
| `session.end` | — | User exits |

#### Server → Client events

| event_type | Key fields | Description |
|---|---|---|
| `session.started` | `current_step`, `instruction` | Session ready, initial prompt |
| `assistant.instruction` | `current_step`, `instruction`, `speak`, `uncertain` | Main guidance event |
| `assistant.status` | `status` | Status update: thinking, listening, etc. |
| `state.update` | `current_step`, full session fields | Step advanced |
| `assistant.error` | `error` | Recoverable error with safe fallback |

#### Message envelope (both directions)

```json
{
  "session_id": "abc123",
  "event_type": "...",
  "...": "..."
}
```

---

## 4. State Machine Pseudocode

```python
# workflow_engine.py

STATES = {
    "intake": {
        "label": "Intake",
        "objective": "Collect initial context. See injury. Understand urgency.",
        "example_instruction": "Show me the injury and tell me what happened.",
        "allowed_next": ["escalation"],
        "auto_advance": False,
    },
    "escalation": {
        "label": "Escalation",
        "objective": "Ensure emergency services are contacted.",
        "example_instruction": "This looks serious. Call emergency services now if you have not already.",
        "allowed_next": ["identify_injury"],
        "auto_advance": True,   # advance after instruction is delivered once
    },
    "identify_injury": {
        "label": "Identify Injury",
        "objective": "Get a clear view of the bleeding site.",
        "example_instruction": "Move the camera closer to the bleeding area.",
        "allowed_next": ["apply_pressure"],
        "auto_advance": False,
    },
    "apply_pressure": {
        "label": "Apply Pressure",
        "objective": "Instruct user to apply direct pressure.",
        "example_instruction": "Press firmly on the wound with a clean cloth or towel now.",
        "allowed_next": ["maintain_pressure"],
        "auto_advance": False,
    },
    "maintain_pressure": {
        "label": "Maintain Pressure",
        "objective": "Reinforce continued pressure.",
        "example_instruction": "Keep steady pressure. If blood soaks through, place more cloth on top.",
        "allowed_next": ["complete"],
        "auto_advance": False,
    },
    "complete": {
        "label": "Complete",
        "objective": "End demo loop cleanly.",
        "example_instruction": "Good. Keep pressure on the wound until help arrives.",
        "allowed_next": [],
        "auto_advance": False,
    },
}


class WorkflowEngine:

    def get_config(self, step: str) -> dict:
        return STATES[step]

    def can_advance(self, current_step: str, to_step: str) -> bool:
        return to_step in STATES[current_step]["allowed_next"]

    def evaluate(
        self,
        session: SessionState,
        interpretation: ModelInterpretation,
        user_action: str | None   # "done" | "repeat" | None
    ) -> WorkflowDecision:
        """
        Core transition logic. Returns a WorkflowDecision.
        The app — not Gemini — decides what happens next.
        """

        step = session.current_step

        # --- User explicitly said they're done ---
        if user_action == "done":
            next_steps = STATES[step]["allowed_next"]
            if next_steps:
                return WorkflowDecision(action="advance", next_step=next_steps[0])
            return WorkflowDecision(action="complete")

        # --- User asked to repeat ---
        if user_action == "repeat":
            return WorkflowDecision(action="repeat", next_step=step)

        # --- Auto-advance states (e.g. escalation) ---
        if STATES[step]["auto_advance"] and session.step_attempts >= 1:
            next_steps = STATES[step]["allowed_next"]
            if next_steps:
                return WorkflowDecision(action="advance", next_step=next_steps[0])

        # --- View is unclear: stay in current step, ask for better angle ---
        if interpretation.view_unclear:
            return WorkflowDecision(action="clarify", next_step=step)

        # --- State-specific model signal checks ---
        if step == "identify_injury":
            if interpretation.injury_visible:
                return WorkflowDecision(action="advance", next_step="apply_pressure")
            return WorkflowDecision(action="repeat", next_step=step)

        if step == "apply_pressure":
            if interpretation.pressure_applied:
                return WorkflowDecision(action="advance", next_step="maintain_pressure")
            return WorkflowDecision(action="repeat", next_step=step)

        if step == "maintain_pressure":
            if session.step_attempts >= 2:
                return WorkflowDecision(action="advance", next_step="complete")
            return WorkflowDecision(action="repeat", next_step=step)

        # --- Default: stay and repeat ---
        return WorkflowDecision(action="repeat", next_step=step)


@dataclass
class WorkflowDecision:
    action: str     # "advance" | "repeat" | "clarify" | "complete"
    next_step: str  # target step name
```

### Transition table

```
intake          + injury described          → escalation
escalation      + delivered once            → identify_injury  (auto)
identify_injury + injury_visible = true     → apply_pressure
identify_injury + view_unclear = true       → identify_injury  (clarify)
apply_pressure  + pressure_applied = true   → maintain_pressure
apply_pressure  + pressure_applied = false  → apply_pressure   (repeat)
maintain_pressure + step_attempts >= 2      → complete
any             + user.done                 → next_step
any             + user.repeat               → same_step
```

---

## 5. WebSocket Loop (main.py sketch)

```python
@app.websocket("/ws/{session_id}")
async def ws_session(websocket: WebSocket, session_id: str):
    await websocket.accept()

    session = session_manager.get(session_id)
    if not session:
        await websocket.close(code=4004)
        return

    system_prompt = build_state_prompt(session.current_step)

    async with gemini_orchestrator.open_session(system_prompt) as gemini:

        # Confirm session ready
        await websocket.send_json(ServerEvent(
            session_id=session_id,
            event_type="session.started",
            current_step=session.current_step,
            instruction=STATES[session.current_step]["example_instruction"],
            speak=True,
        ).dict())

        # Concurrently: receive from client, receive from Gemini
        async def handle_client():
            async for raw in websocket.iter_text():
                event = ClientEvent.parse_raw(raw)
                if event.event_type == "media.frame" and event.frame:
                    await gemini_orchestrator.send_frame(gemini, b64decode(event.frame))
                elif event.event_type == "audio.chunk" and event.audio:
                    await gemini_orchestrator.send_audio(gemini, b64decode(event.audio))
                elif event.event_type == "speech.transcript" and event.transcript:
                    await gemini_orchestrator.send_text(gemini, event.transcript)
                elif event.event_type == "user.done":
                    decision = workflow_engine.evaluate(session, ModelInterpretation(), "done")
                    await apply_decision(decision, session, websocket)
                elif event.event_type == "user.repeat":
                    decision = workflow_engine.evaluate(session, ModelInterpretation(), "repeat")
                    await apply_decision(decision, session, websocket)
                elif event.event_type == "session.end":
                    break

        async def handle_gemini():
            async for item in gemini_orchestrator.receive(gemini):
                if isinstance(item, ModelInterpretation):
                    decision = workflow_engine.evaluate(session, item, None)
                    await apply_decision(decision, session, websocket)
                elif isinstance(item, str):
                    # partial text chunk — forward to transcript
                    await websocket.send_json({
                        "event_type": "assistant.status",
                        "status": "responding",
                        "chunk": item
                    })

        await asyncio.gather(handle_client(), handle_gemini())

    session_manager.end(session_id)
```

---

## 6. Prompt Templates (prompts.py)

```python
BASE_SYSTEM_PROMPT = """
You are a live multimodal guidance assistant for a bounded severe bleeding-control workflow demo.

Your job:
- Interpret the user's spoken input and visible scene together
- Determine whether the injury area is visible enough
- Determine whether the user appears to be applying pressure
- Produce one short, stress-friendly instruction at a time
- Ask for a clearer camera view if uncertain
- Respond in the same language as the user when possible

You must not:
- Invent new protocols or steps
- Give broad medical diagnosis
- Provide long paragraphs
- Present more than one action at a time

Keep responses under 2 sentences. Be direct and calm.
"""

STATE_CONTEXT = {
    "intake":            "Current objective: collect initial context and understand the situation.",
    "escalation":        "Current objective: ensure the user calls emergency services.",
    "identify_injury":   "Current objective: get a clear view of the bleeding site.",
    "apply_pressure":    "Current objective: instruct the user to apply direct pressure to the wound.",
    "maintain_pressure": "Current objective: reinforce continued steady pressure.",
    "complete":          "Current objective: close the session cleanly and reassure the user.",
}

def build_state_prompt(step: str) -> str:
    return BASE_SYSTEM_PROMPT.strip() + "\n\n" + STATE_CONTEXT.get(step, "")
```

---

## 7. File Layout

```
emergency-guidance-agent/
├── docs/
│   ├── PRD.md
│   └── IMPLEMENTATION.md
├── backend/
│   ├── __init__.py
│   ├── main.py
│   ├── models.py
│   ├── session_manager.py
│   ├── workflow_engine.py
│   ├── gemini_orchestrator.py
│   ├── response_formatter.py
│   ├── prompts.py
│   └── config.py
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── styles.css
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## 8. Dependencies (requirements.txt)

```
fastapi>=0.111.0
uvicorn[standard]>=0.29.0
websockets>=12.0
google-genai>=0.8.0
python-dotenv>=1.0.0
pydantic>=2.0.0
```

---

## 9. Open Questions Before Build

1. **Gemini Live media format** — confirm whether backend proxies audio/video or client connects directly to Gemini Live. Backend proxy is safer for state control; direct client reduces latency.
2. **STT path** — use Gemini Live's built-in speech understanding (preferred) or add client-side Web Speech API as fallback?
3. **Frame rate** — start at 1 fps for frames. Tune down if latency is a problem.
4. **TTS** — Gemini Live audio output preferred; browser `speechSynthesis` as fallback.
5. **Structured output** — decide whether to ask Gemini for JSON interpretation fields or parse intent from free text. JSON is more reliable for state transitions.
