import { Camera, CameraOff } from "lucide-react";
import { useRef, useEffect, useState } from "react";

interface CameraPanelProps {
  isActive: boolean;
}

const CameraPanel = ({ isActive }: CameraPanelProps) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [hasPermission, setHasPermission] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isActive) return;

    let stream: MediaStream | null = null;

    const startCamera = async () => {
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: { width: 640, height: 480, facingMode: "environment" },
          audio: false,
        });
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
        setHasPermission(true);
        setError(null);
      } catch {
        setError("Camera access denied");
        setHasPermission(false);
      }
    };

    startCamera();

    return () => {
      stream?.getTracks().forEach((t) => t.stop());
    };
  }, [isActive]);

  return (
    <div className="relative flex-1 min-h-[200px] md:min-h-0 rounded-xl overflow-hidden border border-border bg-card">
      {isActive && hasPermission ? (
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
