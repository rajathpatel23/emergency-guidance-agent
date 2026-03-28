import { useRef, useState, useCallback } from "react";
import { type TranscriptEntry } from "@/components/TranscriptPanel";

const API_BASE = (import.meta.env.VITE_API_URL ?? "http://localhost:8000") as string;
const WS_BASE = API_BASE.replace(/^http/, "ws");

export type SessionStatus =
  | "idle"
  | "connecting"
  | "listening"
  | "thinking"
  | "responding"
  | "ended";

interface SessionState {
  sessionId: string | null;
  status: SessionStatus;
  currentStep: string;
  stepNumber: number;
  totalSteps: number;
  currentInstruction: string;
  uncertain: boolean;
  language: string;
  transcript: TranscriptEntry[];
}

const INITIAL: SessionState = {
  sessionId: null,
  status: "idle",
  currentStep: "idle",
  stepNumber: 0,
  totalSteps: 8,
  currentInstruction: "Press Start CPR Mode to begin.",
  uncertain: false,
  language: "en",
  transcript: [],
};

export function useGuidanceSession() {
  const wsRef = useRef<WebSocket | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const frameIntervalRef = useRef<number | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const [state, setState] = useState<SessionState>(INITIAL);

  // ---------------------------------------------------------------------------
  // Transcript helpers
  // ---------------------------------------------------------------------------

  const addEntry = useCallback((role: "system" | "user", text: string) => {
    setState((prev) => ({
      ...prev,
      transcript: [
        ...prev.transcript,
        { id: crypto.randomUUID(), role, text, timestamp: new Date() },
      ],
    }));
  }, []);

  // ---------------------------------------------------------------------------
  // Frame capture — grabs JPEG from camera every 1s and sends over WebSocket
  // ---------------------------------------------------------------------------

  const startFrameCapture = useCallback(() => {
    if (!canvasRef.current) {
      const c = document.createElement("canvas");
      c.width = 640;
      c.height = 480;
      canvasRef.current = c;
    }
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");

    frameIntervalRef.current = window.setInterval(() => {
      const video = videoRef.current;
      const ws = wsRef.current;
      if (!video || !ctx || !ws || ws.readyState !== WebSocket.OPEN || video.readyState < 2) return;

      ctx.drawImage(video, 0, 0, 640, 480);
      canvas.toBlob(
        (blob) => {
          if (!blob || !ws || ws.readyState !== WebSocket.OPEN) return;
          blob.arrayBuffer().then((buf) => {
            const bytes = new Uint8Array(buf);
            let binary = "";
            bytes.forEach((b) => (binary += String.fromCharCode(b)));
            const b64 = btoa(binary);
            ws.send(JSON.stringify({ type: "frame", data: b64 }));
          });
        },
        "image/jpeg",
        0.7,
      );
    }, 1000);
  }, []);

  const stopFrameCapture = useCallback(() => {
    if (frameIntervalRef.current !== null) {
      clearInterval(frameIntervalRef.current);
      frameIntervalRef.current = null;
    }
  }, []);

  // ---------------------------------------------------------------------------
  // WebSocket message handler
  // ---------------------------------------------------------------------------

  const handleMessage = useCallback(
    (event: MessageEvent) => {
      const msg = JSON.parse(event.data as string);

      switch (msg.type) {
        case "status":
          setState((prev) => ({
            ...prev,
            status: "listening",
            currentStep: msg.current_step ?? prev.currentStep,
          }));
          addEntry("system", "Session started. I am watching and listening.");
          break;

        case "text_chunk":
          setState((prev) => ({ ...prev, status: "responding" }));
          break;

        case "instruction":
          setState((prev) => ({
            ...prev,
            status: "listening",
            currentStep: msg.current_step,
            stepNumber: msg.step_number,
            totalSteps: msg.total_steps,
            currentInstruction: msg.instruction,
            uncertain: msg.uncertain,
            language: msg.language,
          }));
          addEntry("system", msg.instruction);
          break;

        case "state_update":
          setState((prev) => ({ ...prev, currentStep: msg.current_step }));
          break;

        case "error":
          addEntry("system", `Error: ${msg.message}`);
          setState((prev) => ({ ...prev, status: "listening" }));
          break;
      }
    },
    [addEntry],
  );

  // ---------------------------------------------------------------------------
  // Session lifecycle
  // ---------------------------------------------------------------------------

  const start = useCallback(async () => {
    setState((prev) => ({ ...prev, status: "connecting", transcript: [] }));

    // 1. Request camera + mic — both required
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480, facingMode: "environment" },
        audio: true,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
    } catch {
      setState(INITIAL);
      addEntry("system", "Camera and microphone access are required. Please allow both and try again.");
      return;
    }

    // 2. Create backend session
    let sessionId: string;
    try {
      const res = await fetch(`${API_BASE}/session`, { method: "POST" });
      const body = await res.json();
      sessionId = body.session_id;
    } catch {
      stream.getTracks().forEach((t) => t.stop());
      setState(INITIAL);
      addEntry("system", "Could not reach the server. Make sure the backend is running.");
      return;
    }

    // 3. Open WebSocket
    const ws = new WebSocket(`${WS_BASE}/ws/stream/${sessionId}`);
    wsRef.current = ws;

    ws.onopen = () => {
      setState((prev) => ({ ...prev, sessionId, status: "listening" }));
      startFrameCapture();
    };

    ws.onmessage = handleMessage;

    ws.onerror = () => {
      addEntry("system", "Connection lost. Please restart the session.");
      setState((prev) => ({ ...prev, status: "idle" }));
    };

    ws.onclose = () => {
      stopFrameCapture();
    };
  }, [addEntry, handleMessage, startFrameCapture, stopFrameCapture]);

  const end = useCallback(() => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "end" }));
      ws.close();
    }
    stopFrameCapture();
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    setState({ ...INITIAL, status: "ended" });
    addEntry("system", "Session ended.");
  }, [addEntry, stopFrameCapture]);

  // ---------------------------------------------------------------------------
  // User actions
  // ---------------------------------------------------------------------------

  const send = useCallback((msg: object) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(msg));
    }
  }, []);

  const sendTranscript = useCallback(
    (text: string) => {
      send({ type: "transcript", text });
      addEntry("user", text);
    },
    [send, addEntry],
  );

  const sendDone = useCallback(() => {
    send({ type: "user.done" });
    addEntry("user", "Done.");
  }, [send, addEntry]);

  const sendRepeat = useCallback(() => {
    send({ type: "user.repeat" });
    addEntry("user", "Please repeat.");
  }, [send, addEntry]);

  // ---------------------------------------------------------------------------

  return {
    ...state,
    sessionActive: state.status !== "idle" && state.status !== "ended",
    videoRef,
    start,
    end,
    sendDone,
    sendRepeat,
    sendTranscript,
  };
}
