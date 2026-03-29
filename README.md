# Emergency Guidance Agent

## What the product is

**CPR Copilot** (working name) is a **voice-and-video CPR coaching assistant** for lay rescuers. It runs in the browser, uses the device **camera and microphone**, and talks the user through a **fixed, step-by-step flow** for adult CPR-style help: assess the scene, get emergency services, get a clear view of the patient, start chest compressions, and keep going until professional help takes over or the situation changes.

The product is built for **research and demonstration**: it combines **Google Gemini Live** (multimodal understanding and natural speech) with an **application-controlled state machine** so coaching stays on-script and one instruction at a time. It is **not** a certified medical device and **does not** replace training, dispatch, or professional care—users should always follow local emergency numbers and dispatcher guidance.

---

## What it does

- Accepts **live video** and **speech** from the user’s device over a **WebSocket** session
- Tracks the **current step** in a **bounded workflow** (the app owns transitions, not the model alone)
- Delivers **short, speakable** coaching aligned with that step
- Asks for a **clearer camera view** when the scene is hard to interpret
- Can respond in the **user’s language** when supported by the model
- Avoids open-ended diagnosis; prompts emphasize **safety, 911/help, and hands-on CPR guidance**

---

## Architecture (conceptual)

```
Browser (cpr-copilot)
  └── Camera + mic → Pipecat client → WebSocket
        └── Python API (FastAPI) + Pipecat pipeline
              ├── Session manager
              ├── Workflow engine (FSM)
              └── Gemini Live (audio + optional video understanding)
        └── Audio + step updates back to the UI
```

**Principle:** *Gemini interprets; the application decides.* The model suggests wording and scene understanding; **code** advances (or holds) workflow steps.

A **secondary Node/Fastify API** (`apps/api`) shares types with `packages/shared` and can run a **stub** orchestrator for protocol testing without the full Pipecat + Python stack.

---

## Workflow states (CPR coaching)

```
intake → escalation → see_patient → start_compressions → continue_cpr → complete
```

---

## Repo layout

```
emergency-guidance-agent/
├── backend/                  # FastAPI + Pipecat + Gemini Live (primary realtime path)
├── cpr-copilot/              # React + Pipecat client (browser UI)
├── apps/api/                 # Fastify + WebSocket (optional TS stack / stubs)
├── packages/shared/          # Shared TS types (session, workflow, events)
├── docs/                     # PRD, API notes, static HTML
└── package.json              # Monorepo workspaces (Node apps + shared)
```

---

## Getting started

**Prerequisites:** Node ≥ 20, Python 3.10+ with `backend` venv, **Gemini API key** with Live API access.

**Python backend + browser app (typical demo):**

```bash
# Backend
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt  # or install from pyproject if present
cp ../.env.example ../.env       # set GEMINI_API_KEY
uvicorn main:app --reload --port 8000

# Frontend (another terminal)
cd cpr-copilot && npm install && npm run dev
```

Point `cpr-copilot` at the API via `VITE_API_URL` if not using `http://localhost:8000`.

**Secrets:** Put your real `GEMINI_API_KEY` only in a **local** `.env` (repo root or `backend/.env`), never in `.env.example` or in commits. If a key was ever pushed or shared, **revoke it** in [Google AI Studio](https://aistudio.google.com/apikey) and create a new one.

**Node API only (optional):**

```bash
npm install
npm run build -w @emergency-guidance/shared
npm run dev:api
```

---

## Docs

- [PRD](docs/PRD.md) — requirements and guardrails (may predate CPR-specific naming)
- [API](docs/API.md) — HTTP/WebSocket shape
- Optional: [architecture diagram](docs/architecture.html) (open locally in a browser)

---

## Status

Active development: Python **Pipecat + Gemini Live** pipeline, **cpr-copilot** UI, shared types, and optional **Fastify** API for experimentation.
