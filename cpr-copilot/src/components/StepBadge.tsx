const STEP_LABELS: Record<string, { label: string; color: string }> = {
  idle: { label: "STANDBY", color: "bg-muted text-muted-foreground" },
  intake: { label: "ASSESS", color: "bg-warning/15 text-warning border border-warning/30" },
  escalation: { label: "CALL 911", color: "bg-emergency/15 text-emergency border border-emergency/30 pulse-emergency" },
  see_patient: { label: "VIEW", color: "bg-warning/15 text-warning border border-warning/30" },
  start_compressions: { label: "CPR", color: "bg-emergency/15 text-emergency border border-emergency/30" },
  continue_cpr: { label: "CONTINUE", color: "bg-emergency/15 text-emergency border border-emergency/30 pulse-emergency" },
  complete: { label: "COMPLETE", color: "bg-success/15 text-success border border-success/30" },
};

const STEPS_ORDER = [
  "intake",
  "escalation",
  "see_patient",
  "start_compressions",
  "continue_cpr",
  "complete",
];

interface StepBadgeProps {
  currentStep: string;
  stepNumber?: number;
  totalSteps?: number;
}

const StepBadge = ({ currentStep, stepNumber, totalSteps }: StepBadgeProps) => {
  const info = STEP_LABELS[currentStep] ?? STEP_LABELS.idle;
  const currentIndex = STEPS_ORDER.indexOf(currentStep);

  return (
    <div className="flex items-center gap-3">
      <span
        className={`inline-flex items-center px-3 py-1.5 rounded-md text-xs font-mono font-bold tracking-wider ${info.color}`}
      >
        {info.label}
        {stepNumber != null && totalSteps != null && currentStep !== "idle" && (
          <span className="ml-1.5 opacity-60">
            {stepNumber}/{totalSteps}
          </span>
        )}
      </span>
      {currentStep !== "idle" && (
        <div className="flex items-center gap-1">
          {STEPS_ORDER.map((step, i) => (
            <div
              key={step}
              className={`w-2 h-2 rounded-full transition-colors ${
                i < currentIndex ? "bg-success" : i === currentIndex ? "bg-emergency" : "bg-muted"
              }`}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default StepBadge;
