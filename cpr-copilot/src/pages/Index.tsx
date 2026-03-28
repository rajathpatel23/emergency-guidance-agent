import { useState, useCallback } from "react";
import { Heart } from "lucide-react";
import CameraPanel from "@/components/CameraPanel";
import InstructionPanel from "@/components/InstructionPanel";
import ActionBar from "@/components/ActionBar";
import TranscriptPanel, { type TranscriptEntry } from "@/components/TranscriptPanel";
import StepBadge from "@/components/StepBadge";
import DisclaimerBanner from "@/components/DisclaimerBanner";
import useSpeechCommands from "@/hooks/useSpeechCommands";

const WORKFLOW_STEPS = ["intake", "escalation", "identify_injury", "apply_pressure", "maintain_pressure", "complete"] as const;

const Index = () => {
  const [sessionActive, setSessionActive] = useState(false);
  const [currentStep, setCurrentStep] = useState("idle");
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);

  const addEntry = useCallback((role: "system" | "user", text: string) => {
    setTranscript((prev) => [
      ...prev,
      { id: crypto.randomUUID(), role, text, timestamp: new Date() },
    ]);
  }, []);

  const handleStart = () => {
    setSessionActive(true);
    setCurrentStep("intake");
    setTranscript([]);
    addEntry("system", "CPR session started. Assess the scene — is the person responsive?");
  };

  const handleDone = () => {
    const idx = WORKFLOW_STEPS.indexOf(currentStep as typeof WORKFLOW_STEPS[number]);
    if (idx >= 0 && idx < WORKFLOW_STEPS.length - 1) {
      const next = WORKFLOW_STEPS[idx + 1];
      addEntry("user", "Done — moving to next step.");
      setCurrentStep(next);
      const stepMessages: Record<string, string> = {
        escalation: "Good. Now call 911 immediately — put the phone on speaker.",
        identify_injury: "Place the person on their back on a firm, flat surface.",
        apply_pressure: "Begin chest compressions — push hard and fast, center of the chest.",
        maintain_pressure: "Keep going! 30 compressions, then 2 rescue breaths. Don't stop.",
        complete: "Emergency services have arrived. Transfer care to the paramedics.",
      };
      addEntry("system", stepMessages[next] || "Proceeding to next step.");
    }
  };

  const handleRepeat = () => {
    addEntry("user", "Please repeat the instruction.");
    addEntry("system", "Repeating current instruction — follow the guidance on the right panel.");
  };

  const handleEnd = () => {
    setSessionActive(false);
    setCurrentStep("idle");
    addEntry("system", "Session ended.");
  };

  useSpeechCommands({
    enabled: sessionActive,
    onDone: handleDone,
    onRepeat: handleRepeat,
    onTranscript: (text) => addEntry("user", text),
  });

  return (
    <div className="flex flex-col h-screen bg-background overflow-hidden">
      {/* Disclaimer */}
      <DisclaimerBanner />

      {/* Header */}
      <header className="flex items-center justify-between px-3 md:px-5 py-2.5 md:py-3 border-b border-border">
        <div className="flex items-center gap-2 md:gap-3">
          <div className="w-8 h-8 md:w-9 md:h-9 rounded-lg bg-emergency/15 flex items-center justify-center">
            <Heart className="w-4 h-4 md:w-5 md:h-5 text-emergency" />
          </div>
          <div>
            <h1 className="text-base md:text-lg font-bold tracking-tight text-foreground">
              CPR Copilot
            </h1>
            <p className="text-[10px] md:text-[11px] font-mono text-muted-foreground -mt-0.5">
              Emergency Guidance Agent
            </p>
          </div>
        </div>
        <StepBadge currentStep={currentStep} />
      </header>

      {/* Main Content */}
      <div className="flex-1 flex flex-col lg:flex-row min-h-0 p-3 md:p-4 gap-3 md:gap-4 overflow-y-auto">
        {/* Instructions — shown first on mobile for immediate guidance */}
        <div className="lg:order-2 lg:w-[380px] flex-shrink-0">
          <InstructionPanel currentStep={currentStep} />
        </div>

        {/* Camera + Transcript */}
        <div className="flex flex-col flex-1 gap-3 md:gap-4 min-w-0 lg:order-1">
          <CameraPanel isActive={sessionActive} />
          <TranscriptPanel entries={transcript} />
        </div>
      </div>

      {/* Bottom Controls — sticky on mobile */}
      <div className="sticky bottom-0 px-3 pb-3 md:px-4 md:pb-4 bg-background/95 backdrop-blur-sm border-t border-border lg:border-t-0">
        <ActionBar
          sessionActive={sessionActive}
          currentStep={currentStep}
          onStart={handleStart}
          onEnd={handleEnd}
        />
      </div>
    </div>
  );
};

export default Index;
