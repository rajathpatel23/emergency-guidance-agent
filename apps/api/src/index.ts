import Fastify from "fastify";
import cors from "@fastify/cors";
import { createSession, getSession, endSession, updateSession } from "./session-manager.js";
import { createStubGeminiOrchestrator } from "./gemini-orchestrator.js";
import { decideAfterModel, applyWorkflowDecision } from "./workflow-engine.js";
import { formatInstruction } from "./response-formatter.js";
import type { ClientToBackendEvent } from "@emergency-guidance/shared";

const app = Fastify({ logger: true });
const gemini = createStubGeminiOrchestrator();

await app.register(cors);

app.get("/health", async () => ({ status: "ok" }));

app.post("/session", async () => {
  const session = createSession();
  return { session_id: session.session_id };
});

app.get("/ws/:sessionId", { websocket: true }, (socket, req) => {
  const { sessionId } = req.params as { sessionId: string };
  const session = getSession(sessionId);

  if (!session) {
    socket.close(1008, "Session not found");
    return;
  }

  socket.send(JSON.stringify(formatInstruction(session)));

  socket.on("message", async (raw) => {
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
      const decision = { kind: "advance" as const, next: (() => {
        const nexts: Record<string, string> = {
          intake: "escalation",
          escalation: "identify_injury",
          identify_injury: "apply_pressure",
          apply_pressure: "maintain_pressure",
          maintain_pressure: "complete",
          complete: "complete",
        };
        return nexts[current.current_step] as any;
      })() };
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
