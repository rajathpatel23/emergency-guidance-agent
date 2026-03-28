const STEP_LABELS: Record<string, { label: string; color: string }> = {
  idle: { label: "STANDBY", color: "bg-muted text-muted-foreground" },
  intake: { label: "ASSESS", color: "bg-warning/15 text-warning border border-warning/30" },
  escalation: { label: "CALL 911", color: "bg-emergency/15 text-emergency border border-emergency/30 pulse-emergency" },
  identify_injury: { label: "POSITION", color: "bg-warning/15 text-warning border border-warning/30" },
  apply_pressure: { label: "COMPRESSIONS", color: "bg-emergency/15 text-emergency border border-emergency/30" },
  maintain_pressure: { label: "CONTINUE CPR", color: "bg-emergency/15 text-emergency border border-emergency/30 pulse-emergency" },
  complete: { label: "COMPLETE", color: "bg-success/15 text-success border border-success/30" },
};

const STEPS_ORDER = ["intake", "escalation", "identify_injury", "apply_pressure", "maintain_pressure", "complete"];

interface StepBadgeProps {
  currentStep: string;
}

const StepBadge = ({ currentStep }: StepBadgeProps) => {
  const info = STEP_LABELS[currentStep] || STEP_LABELS.idle;
  const currentIndex = STEPS_ORDER.indexOf(currentStep);

  return (
    <div className="flex items-center gap-3">
      <span className={`inline-flex items-center px-3 py-1.5 rounded-md text-xs font-mono font-bold tracking-wider ${info.color}`}>
        {info.label}
      </span>
      {currentStep !== "idle" && (
        <div className="flex items-center gap-1">
          {STEPS_ORDER.map((step, i) => (
            <div
              key={step}
              className={`w-2 h-2 rounded-full transition-colors ${
                i < currentIndex
                  ? "bg-success"
                  : i === currentIndex
                  ? "bg-emergency"
                  : "bg-muted"
              }`}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default StepBadge;
