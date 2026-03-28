import { useRef, useState, useCallback } from "react";
import { PipecatClient } from "@pipecat-ai/client-js";
import { WebSocketTransport } from "@pipecat-ai/websocket-transport";
import { ProtobufFrameSerializerCompat } from "@/lib/protobufSerializerCompat";
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
  totalSteps: 6,
  currentInstruction: "Press Start CPR Mode to begin.",
  uncertain: false,
  language: "en",
  transcript: [],
};

export function useGuidanceSession() {
  const clientRef = useRef<PipecatClient | null>(null);
  const transportRef = useRef<WebSocketTransport | null>(null);
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
  // Video frame capture — sends JPEG frames as raw WebSocket messages
  // ---------------------------------------------------------------------------

  const startFrameCapture = useCallback((transport: WebSocketTransport) => {
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
            transport.sendRawMessage({ type: "frame", data: b64 });
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

    // 2. Camera only for preview. Pipecat's transport opens a *separate* mic
    //    stream on connect (see WebSocketTransport.initDevices → WavRecorder.begin).
    //    If we also grab the microphone here, many browsers fail the second
    //    capture or leave it silent — so Gemini never "hears" you.
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
      addEntry("system", "Camera access is required. Please allow the camera and try again.");
      return;
    }

    // 3. Build Pipecat WebSocket transport with protobuf serialization
    const transport = new WebSocketTransport({
      wsUrl: `${WS_BASE}/ws/stream/${sessionId}`,
      serializer: new ProtobufFrameSerializerCompat(),
      recorderSampleRate: 16000, // must match Pipecat default / Gemini Live input
      playerSampleRate: 24000, // Gemini Live TTS output
    });
    transportRef.current = transport;

    const client = new PipecatClient({
      transport,
      enableMic: true,
    });
    clientRef.current = client;

    client.on("connected", () => {
      setState((prev) => ({ ...prev, sessionId, status: "listening" }));
      addEntry("system", "Session started. I am watching and listening.");
      startFrameCapture(transport);
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

    const pushBotText = (raw: unknown) => {
      const text =
        typeof raw === "string"
          ? raw
          : raw && typeof raw === "object" && "text" in raw
            ? String((raw as { text: string }).text)
            : "";
      if (!text.trim()) return;
      setState((prev) => ({ ...prev, currentInstruction: text }));
      addEntry("system", text);
    };

    // Prefer botOutput (current); botTranscript is deprecated in client-js but still wire it.
    client.on("botOutput", pushBotText);
    client.on("botTranscript", pushBotText);

    client.on("userTranscript", (data: { text?: string; final?: boolean }) => {
      const t = data.text?.trim();
      if (!t) return;
      if (data.final) addEntry("user", t);
    });

    // State updates pushed from backend workflow engine
    client.on("serverMessage", (msg: Record<string, unknown>) => {
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

    client.on("error", (err: { data?: unknown; type?: string }) => {
      const msg = err?.data !== undefined ? JSON.stringify(err.data) : (err?.type ?? "unknown error");
      addEntry("system", `Error: ${msg}`);
    });

    try {
      // Open microphone before WS so permission errors are obvious; connect() also calls
      // initDevices when needed, but explicit call gives a clearer failure mode.
      await client.initDevices();
      await client.connect();
    } catch (e) {
      stopFrameCapture();
      clientRef.current = null;
      transportRef.current = null;
      const video = videoRef.current;
      if (video?.srcObject) {
        (video.srcObject as MediaStream).getTracks().forEach((t) => t.stop());
        video.srcObject = null;
      }
      setState(INITIAL);
      const message =
        e instanceof Error ? e.message : "Could not start voice session (check mic permission).";
      addEntry("system", message);
    }
  }, [addEntry, startFrameCapture, stopFrameCapture]);

  const end = useCallback(() => {
    stopFrameCapture();
    clientRef.current?.disconnect();
    clientRef.current = null;
    transportRef.current = null;

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
  // User actions — sent as RTVIMessages, backend workflow engine handles them
  // ---------------------------------------------------------------------------

  /** RTVI client-message — backend can handle types like user.done / user.repeat if wired. */
  const sendAction = useCallback((type: string, extra?: Record<string, unknown>) => {
    clientRef.current?.sendClientMessage(type, extra ?? {});
  }, []);

  const sendDone = useCallback(() => {
    sendAction("user.done", {});
    addEntry("user", "Done.");
  }, [sendAction, addEntry]);

  const sendRepeat = useCallback(() => {
    sendAction("user.repeat", {});
    addEntry("user", "Please repeat.");
  }, [sendAction, addEntry]);

  /**
   * Browser Web Speech → Gemini via RTVI `send-text` (not the removed sendMessage API).
   */
  const sendTranscript = useCallback(
    (text: string) => {
      const client = clientRef.current;
      if (client) void client.sendText(text);
      addEntry("user", text);
    },
    [addEntry],
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
