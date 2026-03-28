/**
 * PRD §19 — Event names for client ↔ server WebSocket channel.
 * Internal backend events (model.interpretation, workflow.*) are not shared types.
 */
export type ClientEventType =
  | "session.start"
  | "media.frame"
  | "audio.chunk"
  | "speech.transcript"
  | "user.done"
  | "user.repeat"
  | "session.end";

export type ResponseEventType =
  | "assistant.instruction"
  | "assistant.status"
  | "assistant.error";

export type UiSessionStatus = "listening" | "thinking" | "responding" | "idle" | "error";
