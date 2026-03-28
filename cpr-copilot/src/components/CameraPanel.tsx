import { Camera, CameraOff } from "lucide-react";
import { type RefObject } from "react";

interface CameraPanelProps {
  isActive: boolean;
  /** Video ref owned by useGuidanceSession — stream managed by the hook */
  videoRef: RefObject<HTMLVideoElement>;
  error?: string | null;
}

const CameraPanel = ({ isActive, videoRef, error }: CameraPanelProps) => {
  return (
    <div className="relative flex-1 min-h-0 rounded-xl overflow-hidden border border-border bg-card">
      {isActive ? (
        <>
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className="w-full h-full object-cover"
          />
          <div className="absolute inset-0 camera-grid pointer-events-none" />
          <div className="absolute top-3 left-3 flex items-center gap-2 bg-background/80 backdrop-blur-sm rounded-md px-2.5 py-1.5">
            <span className="w-2 h-2 rounded-full bg-emergency animate-pulse" />
            <span className="text-xs font-mono text-foreground/80">LIVE</span>
          </div>
        </>
      ) : (
        <div className="w-full h-full flex flex-col items-center justify-center gap-3 bg-card">
          {error ? (
            <CameraOff className="w-10 h-10 text-muted-foreground" />
          ) : (
            <Camera className="w-10 h-10 text-muted-foreground" />
          )}
          <p className="text-sm text-muted-foreground font-mono">
            {error || "Camera will activate when session starts"}
          </p>
        </div>
      )}
    </div>
  );
};

export default CameraPanel;
