import Fastify from "fastify";
import cors from "@fastify/cors";
import websocket from "@fastify/websocket";
import { createSession, getSession, endSession, updateSession } from "./session-manager.js";
import { createStubGeminiOrchestrator } from "./gemini-orchestrator.js";
import { decideAfterModel, applyWorkflowDecision } from "./workflow-engine.js";
import { formatInstruction } from "./response-formatter.js";
import type { ClientToBackendEvent, WorkflowStep } from "@emergency-guidance/shared";

const app = Fastify({ logger: true });
const gemini = createStubGeminiOrchestrator();

await app.register(cors);
await app.register(websocket);

app.get("/health", async () => ({ status: "ok" }));

app.post("/session", async () => {
  const session = createSession();
  return { session_id: session.session_id };
});

app.get<{ Params: { sessionId: string } }>("/ws/:sessionId", { websocket: true }, (socket, req) => {
  const sessionId = req.params.sessionId;
  const session = getSession(sessionId);

  if (!session) {
    socket.close(1008, "Session not found");
    return;
  }

  socket.send(JSON.stringify(formatInstruction(session)));

  socket.on("message", async (raw: Buffer | ArrayBuffer | Buffer[]) => {
    let event: ClientToBackendEvent;
    try {
      event = JSON.parse(raw.toString()) as ClientToBackendEvent;
    } catch {
      return;
    }

    const current = getSession(sessionId);
    if (!current || current.status === "ended") return;

    if (event.event_type === "session.end") {
      endSession(sessionId);
      socket.close();
      return;
    }

    if (event.event_type === "user.done") {
      const nexts: Record<WorkflowStep, WorkflowStep> = {
        intake: "escalation",
        escalation: "see_patient",
        see_patient: "start_compressions",
        start_compressions: "continue_cpr",
        continue_cpr: "complete",
        complete: "complete",
      };
      const decision = { kind: "advance" as const, next: nexts[current.current_step] };
      const next = applyWorkflowDecision(current, decision);
      updateSession(sessionId, next);
      socket.send(JSON.stringify(formatInstruction(next)));
      return;
    }

    if (event.event_type === "user.repeat") {
      socket.send(JSON.stringify(formatInstruction(current)));
      return;
    }

    if (
      event.event_type === "speech.transcript" ||
      event.event_type === "media.frame"
    ) {
      const interpretation = await gemini.interpret({
        state: current,
        transcript: event.transcript,
        frameBase64: event.frame,
      });
      const decision = decideAfterModel(current, interpretation);
      const next = applyWorkflowDecision(current, decision);
      updateSession(sessionId, next);
      socket.send(JSON.stringify(formatInstruction(next)));
    }
  });
});

const port = Number(process.env.PORT ?? 3001);
await app.listen({ port, host: "0.0.0.0" });
