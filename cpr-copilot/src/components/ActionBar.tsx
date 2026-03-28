import { Play, Square, Mic } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ActionBarProps {
  sessionActive: boolean;
  currentStep: string;
  onStart: () => void;
  onEnd: () => void;
}

const ActionBar = ({ sessionActive, onStart, onEnd }: ActionBarProps) => {
  return (
    <div className="flex items-center gap-3 p-4 rounded-xl border border-border bg-card">
      {!sessionActive ? (
        <Button
          onClick={onStart}
          className="flex-1 h-14 text-lg font-bold bg-emergency hover:bg-emergency-glow text-emergency-foreground emergency-glow transition-all"
        >
          <Play className="w-5 h-5 mr-2" />
          Start CPR Mode
        </Button>
      ) : (
        <>
          <div className="flex-1 flex items-center gap-3 px-4 h-12 rounded-lg bg-secondary/50 border border-border">
            <Mic className="w-4 h-4 text-emergency animate-pulse" />
            <span className="text-sm font-mono text-muted-foreground">
              Listening… say <span className="text-foreground font-semibold">"Done"</span> or <span className="text-foreground font-semibold">"Repeat"</span>
            </span>
          </div>
          <Button
            onClick={onEnd}
            variant="outline"
            className="h-12 px-4 font-semibold border-emergency/30 text-emergency hover:bg-emergency/10"
          >
            <Square className="w-4 h-4" />
          </Button>
        </>
      )}
    </div>
  );
};

export default ActionBar;
