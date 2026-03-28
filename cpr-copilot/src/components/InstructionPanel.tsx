import { AlertTriangle } from "lucide-react";

const STEP_META: Record<string, { title: string; fallback: string; detail: string }> = {
  idle: {
    title: "Ready",
    fallback: "Press 'Start CPR Mode' to begin",
    detail: "Ensure you are safe and the patient is on a flat surface.",
  },
  intake: {
    title: "Assess the Scene",
    fallback: "Check if the person is responsive",
    detail: "Tap their shoulders and shout 'Are you okay?' Look for signs of breathing.",
  },
  check_responsiveness: {
    title: "Check Responsiveness",
    fallback: "Tap their shoulders and ask if they are okay",
    detail: "Look for signs of breathing or movement.",
  },
  call_emergency: {
    title: "Call for Help",
    fallback: "Call emergency services now",
    detail: "If someone else is present, ask them to call. Put the phone on speaker.",
  },
  position_hands: {
    title: "Position Hands",
    fallback: "Place your hands in the center of the chest",
    detail: "Heel of one hand on the breastbone, interlock fingers, arms straight.",
  },
  start_compressions: {
    title: "Begin Compressions",
    fallback: "Push hard and fast — at least 2 inches deep",
    detail: "100–120 compressions per minute. Let the chest fully rise between compressions.",
  },
  keep_rhythm: {
    title: "Keep Rhythm",
    fallback: "Keep a steady pace — push to the beat",
    detail: "Do not stop. Push hard, push fast. Count aloud if it helps.",
  },
  continue_loop: {
    title: "Continue CPR",
    fallback: "Keep going — do not stop until help arrives",
    detail: "30 compressions, then 2 rescue breaths. Repeat the cycle.",
  },
  complete: {
    title: "Help Has Arrived",
    fallback: "Transfer care to emergency services",
    detail: "Brief the paramedics on what happened and how long you performed CPR.",
  },
};

const RHYTHM_STEPS = ["start_compressions", "keep_rhythm", "continue_loop"];

interface InstructionPanelProps {
  currentStep: string;
  /** Live instruction from Gemini — overrides fallback text when present */
  liveInstruction?: string;
  uncertain?: boolean;
}

const InstructionPanel = ({ currentStep, liveInstruction, uncertain }: InstructionPanelProps) => {
  const meta = STEP_META[currentStep] ?? STEP_META.idle;
  const instruction = liveInstruction?.trim() || meta.fallback;

  return (
    <div className="flex flex-col gap-4 p-5 rounded-xl border border-border bg-card h-full">
      <div className="flex items-center gap-2">
        <AlertTriangle className="w-5 h-5 text-emergency" />
        <h2 className="text-sm font-mono font-semibold uppercase tracking-wider text-emergency">
          {meta.title}
        </h2>
        {uncertain && (
          <span className="ml-auto text-xs font-mono text-warning bg-warning/10 border border-warning/20 px-2 py-0.5 rounded">
            Move camera closer
          </span>
        )}
      </div>

      <div className="flex-1 flex flex-col justify-center gap-4">
        <p className="text-2xl font-bold leading-tight text-foreground">
          {instruction}
        </p>
        {!liveInstruction && (
          <p className="text-sm leading-relaxed text-muted-foreground">
            {meta.detail}
          </p>
        )}
      </div>

      {RHYTHM_STEPS.includes(currentStep) && (
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
