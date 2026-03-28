import { AlertTriangle } from "lucide-react";

const STEP_INSTRUCTIONS: Record<string, { title: string; instruction: string; detail: string }> = {
  idle: {
    title: "Ready",
    instruction: "Press 'Start CPR Mode' to begin",
    detail: "Ensure you are safe and the patient is on a flat surface.",
  },
  intake: {
    title: "Assess the Scene",
    instruction: "Check if the person is responsive",
    detail: "Tap their shoulders and shout 'Are you okay?' Look for signs of breathing.",
  },
  escalation: {
    title: "Call for Help",
    instruction: "Call 911 immediately",
    detail: "If someone else is present, ask them to call. Put the phone on speaker.",
  },
  identify_injury: {
    title: "Position the Patient",
    instruction: "Place the person on their back on a firm surface",
    detail: "Tilt their head back slightly, lift their chin to open the airway.",
  },
  apply_pressure: {
    title: "Begin Compressions",
    instruction: "Push hard and fast in the center of the chest",
    detail: "Place the heel of one hand on the center of the chest, interlock fingers. Push at least 2 inches deep, 100–120 compressions per minute.",
  },
  maintain_pressure: {
    title: "Continue CPR",
    instruction: "Keep going — 30 compressions, then 2 rescue breaths",
    detail: "Do not stop until help arrives or the person starts breathing. Push hard, push fast.",
  },
  complete: {
    title: "Help Has Arrived",
    instruction: "Transfer care to emergency services",
    detail: "Brief the paramedics on what happened and how long you performed CPR.",
  },
};

interface InstructionPanelProps {
  currentStep: string;
}

const InstructionPanel = ({ currentStep }: InstructionPanelProps) => {
  const info = STEP_INSTRUCTIONS[currentStep] || STEP_INSTRUCTIONS.idle;

  return (
    <div className="flex flex-col gap-3 md:gap-4 p-4 md:p-5 rounded-xl border border-border bg-card h-full">
      <div className="flex items-center gap-2">
        <AlertTriangle className="w-5 h-5 text-emergency" />
        <h2 className="text-sm font-mono font-semibold uppercase tracking-wider text-emergency">
          {info.title}
        </h2>
      </div>

      <div className="flex-1 flex flex-col justify-center gap-3 md:gap-4">
        <p className="text-xl md:text-2xl font-bold leading-tight text-foreground">
          {info.instruction}
        </p>
        <p className="text-sm leading-relaxed text-muted-foreground">
          {info.detail}
        </p>
      </div>

      {currentStep === "apply_pressure" && (
        <div className="flex items-center gap-3 p-3 rounded-lg bg-emergency/10 border border-emergency/20">
          <div className="w-3 h-3 rounded-full bg-emergency pulse-emergency" />
          <span className="text-sm font-mono text-emergency">
            100–120 BPM — Push to the beat
          </span>
        </div>
      )}
    </div>
  );
};

export default InstructionPanel;
