import { ShieldAlert } from "lucide-react";

const DisclaimerBanner = () => {
  return (
    <div className="flex items-center gap-2.5 px-4 py-2 bg-emergency/10 border-b border-emergency/20">
      <ShieldAlert className="w-4 h-4 text-emergency flex-shrink-0" />
      <p className="text-xs text-emergency/80 font-mono">
        <span className="font-bold text-emergency">FOR DEMO ONLY</span> — Not a substitute for professional medical care. Always call 911 first.
      </p>
    </div>
  );
};

export default DisclaimerBanner;
