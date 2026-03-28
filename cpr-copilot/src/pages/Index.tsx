import { Heart } from "lucide-react";
import CameraPanel from "@/components/CameraPanel";
import InstructionPanel from "@/components/InstructionPanel";
import ActionBar from "@/components/ActionBar";
import TranscriptPanel from "@/components/TranscriptPanel";
import StepBadge from "@/components/StepBadge";
import DisclaimerBanner from "@/components/DisclaimerBanner";
import useSpeechCommands from "@/hooks/useSpeechCommands";
import { useGuidanceSession } from "@/hooks/useGuidanceSession";

const Index = () => {
  const session = useGuidanceSession();

  useSpeechCommands({
    enabled: session.sessionActive,
    onDone: session.sendDone,
    onRepeat: session.sendRepeat,
    onTranscript: session.sendTranscript,
  });

  return (
    <div className="flex flex-col h-screen bg-background overflow-hidden">
      <DisclaimerBanner />

      <header className="flex items-center justify-between px-5 py-3 border-b border-border">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-emergency/15 flex items-center justify-center">
            <Heart className="w-5 h-5 text-emergency" />
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight text-foreground">
              CPR Copilot
            </h1>
            <p className="text-[11px] font-mono text-muted-foreground -mt-0.5">
              Emergency Guidance Agent
            </p>
          </div>
        </div>
        <StepBadge
          currentStep={session.currentStep}
          stepNumber={session.stepNumber}
          totalSteps={session.totalSteps}
        />
      </header>

      <div className="flex-1 flex min-h-0 p-4 gap-4">
        <div className="flex flex-col flex-1 gap-4 min-w-0">
          <CameraPanel
            isActive={session.sessionActive}
            videoRef={session.videoRef}
          />
          <TranscriptPanel entries={session.transcript} />
        </div>

        <div className="w-[380px] flex-shrink-0">
          <InstructionPanel
            currentStep={session.currentStep}
            liveInstruction={session.currentInstruction}
            uncertain={session.uncertain}
          />
        </div>
      </div>

      <div className="px-4 pb-4">
        <ActionBar
          sessionActive={session.sessionActive}
          currentStep={session.currentStep}
          onStart={session.start}
          onEnd={session.end}
        />
      </div>
    </div>
  );
};

export default Index;
