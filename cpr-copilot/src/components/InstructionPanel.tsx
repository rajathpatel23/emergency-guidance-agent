import { AlertTriangle } from "lucide-react";

/** Step ids match backend `workflow_engine.STATES` */
const STEP_META: Record<string, { title: string; fallback: string; detail: string }> = {
  idle: {
    title: "Ready",
    fallback: "Press 'Start CPR Mode' to begin",
    detail: "Ensure you are safe and the scene is safe before you begin.",
  },
  intake: {
    title: "Assess the Scene",
    fallback: "Show me the injury and tell me what happened",
    detail: "Describe what you see and how severe the bleeding appears.",
  },
  escalation: {
    title: "Call for Help",
    fallback: "Call emergency services now if you have not already",
    detail: "If someone else is present, ask them to call. Put the phone on speaker.",
  },
  identify_injury: {
    title: "View the Injury",
    fallback: "Move the camera closer to the bleeding area",
    detail: "We need a clear view of the wound to guide the next step.",
  },
  apply_pressure: {
    title: "Apply Pressure",
    fallback: "Press firmly on the wound with a clean cloth or towel now",
    detail: "Cover the wound and press directly on the bleeding site.",
  },
  maintain_pressure: {
    title: "Maintain Pressure",
    fallback: "Keep steady pressure — do not lift the cloth to look",
    detail: "If blood soaks through, place more cloth on top and keep pressing.",
  },
  complete: {
    title: "Help on the Way",
    fallback: "Keep pressure on the wound until help arrives",
    detail: "Brief responders on what happened when they arrive.",
  },
};

interface InstructionPanelProps {
  currentStep: string;
  /** Live instruction from the model — overrides fallback when present */
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
        <p className="text-2xl font-bold leading-tight text-foreground">{instruction}</p>
        {!liveInstruction?.trim() && (
          <p className="text-sm leading-relaxed text-muted-foreground">{meta.detail}</p>
        )}
      </div>

      {currentStep === "apply_pressure" && (
        <div className="flex items-center gap-3 p-3 rounded-lg bg-emergency/10 border border-emergency/20">
          <div className="w-3 h-3 rounded-full bg-emergency pulse-emergency" />
          <span className="text-sm font-mono text-emergency">100–120 BPM — Push to the beat</span>
        </div>
      )}
    </div>
  );
};

export default InstructionPanel;
