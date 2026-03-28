import { useRef, useEffect } from "react";
import { Bot, User } from "lucide-react";

export interface TranscriptEntry {
  id: string;
  role: "system" | "user";
  text: string;
  timestamp: Date;
}

interface TranscriptPanelProps {
  entries: TranscriptEntry[];
}

const TranscriptPanel = ({ entries }: TranscriptPanelProps) => {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [entries]);

  return (
    <div className="flex flex-col rounded-xl border border-border bg-card overflow-hidden">
      <div className="px-4 py-2.5 border-b border-border bg-secondary/50">
        <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-muted-foreground">
          Transcript
        </h3>
      </div>
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-3 space-y-2 max-h-48 min-h-[120px]">
        {entries.length === 0 ? (
          <p className="text-xs text-muted-foreground font-mono text-center py-4">
            Session transcript will appear here…
          </p>
        ) : (
          entries.map((entry) => (
            <div key={entry.id} className="flex gap-2.5 items-start">
              <div
                className={`w-6 h-6 rounded-md flex items-center justify-center flex-shrink-0 mt-0.5 ${
                  entry.role === "system"
                    ? "bg-emergency/15 text-emergency"
                    : "bg-secondary text-muted-foreground"
                }`}
              >
                {entry.role === "system" ? <Bot className="w-3.5 h-3.5" /> : <User className="w-3.5 h-3.5" />}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-foreground leading-relaxed">{entry.text}</p>
                <span className="text-[10px] font-mono text-muted-foreground">
                  {entry.timestamp.toLocaleTimeString()}
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default TranscriptPanel;
