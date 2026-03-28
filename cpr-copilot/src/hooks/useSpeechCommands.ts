import { useEffect, useRef, useCallback } from "react";

interface SpeechCommandsOptions {
  enabled: boolean;
  onDone: () => void;
  onRepeat: () => void;
  onTranscript?: (text: string) => void;
}

const useSpeechCommands = ({ enabled, onDone, onRepeat, onTranscript }: SpeechCommandsOptions) => {
  const recognitionRef = useRef<any>(null);
  const isListeningRef = useRef(false);

  const startListening = useCallback(() => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      console.warn("Speech Recognition API not supported in this browser.");
      return;
    }

    if (recognitionRef.current) {
      recognitionRef.current.abort();
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.lang = "en-US";

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      for (let i = event.resultIndex; i < event.results.length; i++) {
        if (event.results[i].isFinal) {
          const transcript = event.results[i][0].transcript.trim().toLowerCase();
          onTranscript?.(event.results[i][0].transcript.trim());

          if (transcript.includes("done") || transcript.includes("next") || transcript.includes("proceed")) {
            onDone();
          } else if (transcript.includes("repeat") || transcript.includes("again") || transcript.includes("say that again")) {
            onRepeat();
          }
        }
      }
    };

    recognition.onerror = (event) => {
      if (event.error !== "aborted" && event.error !== "no-speech") {
        console.error("Speech recognition error:", event.error);
      }
    };

    recognition.onend = () => {
      // Auto-restart if still enabled
      if (isListeningRef.current) {
        try {
          recognition.start();
        } catch {
          // ignore
        }
      }
    };

    recognitionRef.current = recognition;
    isListeningRef.current = true;

    try {
      recognition.start();
    } catch {
      // ignore
    }
  }, [onDone, onRepeat, onTranscript]);

  const stopListening = useCallback(() => {
    isListeningRef.current = false;
    if (recognitionRef.current) {
      recognitionRef.current.abort();
      recognitionRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (enabled) {
      startListening();
    } else {
      stopListening();
    }
    return stopListening;
  }, [enabled, startListening, stopListening]);

  return { isListening: enabled };
};

export default useSpeechCommands;
