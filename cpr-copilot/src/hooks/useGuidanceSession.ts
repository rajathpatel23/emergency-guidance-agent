import { useRef, useState, useCallback } from "react";
import { PipecatClient } from "@pipecat-ai/client-js";
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
  const clientRef = useRef<PipecatClient | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const frameIntervalRef = useRef<number | null>(null);

  const [state, setState] = useState<SessionState>(INITIAL);

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
  // Video frame capture — sends JPEG frames via Pipecat client messages
  // ---------------------------------------------------------------------------

  const startFrameCapture = useCallback((client: PipecatClient) => {
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
      if (!video || !ctx || video.readyState < 2) return;
      ctx.drawImage(video, 0, 0, 640, 480);
      canvas.toBlob(
        (blob) => {
          if (!blob) return;
          blob.arrayBuffer().then((buf) => {
            const bytes = new Uint8Array(buf);
            let binary = "";
            bytes.forEach((b) => (binary += String.fromCharCode(b)));
            const b64 = btoa(binary);
            // Send as a custom app message alongside the audio pipeline
            client.sendMessage({ type: "frame", data: b64 });
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
  // Session lifecycle
  // ---------------------------------------------------------------------------

  const start = useCallback(async () => {
    setState((prev) => ({ ...prev, status: "connecting", transcript: [] }));

    // 1. Create backend session
    let sessionId: string;
    try {
      const res = await fetch(`${API_BASE}/session`, { method: "POST" });
      const body = await res.json();
      sessionId = body.session_id;
    } catch {
      setState(INITIAL);
      addEntry("system", "Could not reach the server. Make sure the backend is running.");
      return;
    }

    // 2. Request camera stream (video only — Pipecat handles mic)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480, facingMode: "environment" },
        audio: false,
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
    } catch {
      setState(INITIAL);
      addEntry("system", "Camera access is required. Please allow camera access and try again.");
      return;
    }

    // 3. Connect Pipecat client (handles mic capture + audio pipeline)
    const client = new PipecatClient({
      transport: {
        url: `${WS_BASE}/ws/stream/${sessionId}`,
        enableMic: true,
        enableCam: false, // we handle video frames manually
      } as any,
    });

    clientRef.current = client;

    client.on("connected", () => {
      setState((prev) => ({ ...prev, sessionId, status: "listening" }));
      addEntry("system", "Session started. I am watching and listening.");
      startFrameCapture(client);
    });

    client.on("disconnected", () => {
      stopFrameCapture();
      setState((prev) =>
        prev.status === "ended" ? prev : { ...prev, status: "idle" },
      );
    });

    client.on("botStartedSpeaking", () => {
      setState((prev) => ({ ...prev, status: "responding" }));
    });

    client.on("botStoppedSpeaking", () => {
      setState((prev) => ({ ...prev, status: "listening" }));
    });

    client.on("userStartedSpeaking", () => {
      setState((prev) => ({ ...prev, status: "thinking" }));
    });

    client.on("botTranscript", (data: { text: string }) => {
      setState((prev) => ({ ...prev, currentInstruction: data.text }));
      addEntry("system", data.text);
    });

    client.on("userTranscript", (data: { text: string; final: boolean }) => {
      if (data.final) addEntry("user", data.text);
    });

    // Custom app messages from backend (state updates, step changes)
    client.on("appMessage", (msg: Record<string, unknown>) => {
      if (msg.type === "state_update") {
        setState((prev) => ({
          ...prev,
          currentStep: (msg.current_step as string) ?? prev.currentStep,
          stepNumber: (msg.step_number as number) ?? prev.stepNumber,
          totalSteps: (msg.total_steps as number) ?? prev.totalSteps,
          uncertain: (msg.uncertain as boolean) ?? prev.uncertain,
        }));
      }
    });

    client.on("error", (err: Error) => {
      addEntry("system", `Error: ${err.message}`);
    });

    await client.connect();
  }, [addEntry, startFrameCapture, stopFrameCapture]);

  const end = useCallback(() => {
    stopFrameCapture();
    clientRef.current?.disconnect();
    clientRef.current = null;

    // Stop camera stream
    const video = videoRef.current;
    if (video?.srcObject) {
      (video.srcObject as MediaStream).getTracks().forEach((t) => t.stop());
      video.srcObject = null;
    }

    setState({ ...INITIAL, status: "ended" });
    addEntry("system", "Session ended.");
  }, [addEntry, stopFrameCapture]);

  // ---------------------------------------------------------------------------
  // User actions — sent as app messages, backend workflow engine handles them
  // ---------------------------------------------------------------------------

  const sendAction = useCallback(
    (type: string, extra?: Record<string, unknown>) => {
      clientRef.current?.sendMessage({ type, ...extra });
    },
    [],
  );

  const sendDone = useCallback(() => {
    sendAction("user.done");
    addEntry("user", "Done.");
  }, [sendAction, addEntry]);

  const sendRepeat = useCallback(() => {
    sendAction("user.repeat");
    addEntry("user", "Please repeat.");
  }, [sendAction, addEntry]);

  const sendTranscript = useCallback(
    (text: string) => {
      sendAction("transcript", { text });
      addEntry("user", text);
    },
    [sendAction, addEntry],
  );

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
