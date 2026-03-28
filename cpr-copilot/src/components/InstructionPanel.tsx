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
    fallback: "Tell me what happened—is the person breathing and responsive?",
    detail: "Say if they’re awake, breathing, or unresponsive so we can coach the right steps.",
  },
  escalation: {
    title: "Call for Help",
    fallback: "Call emergency services now if you have not already",
    detail: "If someone else is present, ask them to call. Put the phone on speaker.",
  },
  see_patient: {
    title: "View the Patient",
    fallback: "Show me the person on their back—chest visible if you can",
    detail: "We need a clear, steady view to coach hand placement and compressions.",
  },
  start_compressions: {
    title: "Start Compressions",
    fallback: "Hands on the center of the chest—push hard and fast",
    detail: "Heel of one hand, other on top, shoulders over hands, full recoil between pushes.",
  },
  continue_cpr: {
    title: "Keep Going",
    fallback: "Stay at 100 to 120 compressions per minute—depth and full chest rise",
    detail: "Switch with another rescuer about every two minutes if you can. Minimal pauses.",
  },
  complete: {
    title: "Help on the Way",
    fallback: "Continue CPR until EMS takes over or the person responds",
    detail: "When responders arrive, tell them how long CPR was in progress.",
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

      {currentStep === "start_compressions" && (
        <div className="flex items-center gap-3 p-3 rounded-lg bg-emergency/10 border border-emergency/20">
          <div className="w-3 h-3 rounded-full bg-emergency pulse-emergency" />
          <span className="text-sm font-mono text-emergency">100–120 BPM — Push to the beat</span>
        </div>
      )}
    </div>
  );
};

export default InstructionPanel;
