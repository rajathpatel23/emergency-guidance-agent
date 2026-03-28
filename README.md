# Emergency Guidance Agent

A real-time multimodal assistant that watches a live camera feed, listens to spoken input, and guides a user through a high-stress physical task one step at a time.

MVP workflow: **severe bleeding control**

---

## What it does

- Accepts live video and speech from the user's device
- Tracks the current step in a bounded protocol
- Gives one short actionable instruction at a time
- Asks for a better camera angle when the scene is unclear
- Responds in the user's language (multilingual via Gemini Live)
- Stays strictly within the defined workflow — no open-ended diagnosis

---

## Architecture

```
Frontend (browser)
  └── camera + mic capture
  └── WebSocket → Backend
        └── Session Manager
        └── Workflow Engine (FSM)
        └── Gemini Live Orchestrator
        └── Response Formatter
              └── Gemini Flash Live (multimodal reasoning)
```

The guiding principle: **Gemini interprets. The application decides.**

Gemini handles scene understanding and response phrasing. The workflow engine (app code) owns all state transitions. The model cannot advance the protocol on its own.

---

## Workflow states

```
intake → escalation → identify_injury → apply_pressure → maintain_pressure → complete
```

---

## Repo structure

```
emergency-guidance-agent/
├── apps/
│   └── api/                  # Fastify backend (TypeScript)
│       └── src/
│           ├── workflow-engine.ts
│           ├── session-manager.ts
│           ├── gemini-orchestrator.ts
│           ├── response-formatter.ts
│           └── prompts/
├── packages/
│   └── shared/               # Shared types: events, session state, API contracts
├── docs/
│   ├── PRD.md
│   └── IMPLEMENTATION.md
├── .env.example
└── package.json
```

---

## Getting started

**Prerequisites:** Node >= 20, a Gemini API key with Live API access

```bash
cp .env.example .env
# add your GEMINI_API_KEY to .env

npm install
npm run dev:api
```

Frontend is not yet wired — the API runs on `http://localhost:3001` by default.

---

## Docs

- [PRD](docs/PRD.md) — product requirements, workflow definition, safety guardrails
- [Implementation](docs/IMPLEMENTATION.md) — component tree, module signatures, API contracts, state machine pseudocode

---

## Status

Early scaffold. Backend module structure and shared types are in place. Gemini Live integration and frontend are next.
