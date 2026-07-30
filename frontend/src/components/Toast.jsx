import { useEffect } from "react";

export default function Toast({ message, type = "error", onClose }) {
  useEffect(() => {
    const timer = setTimeout(onClose, 5000);
    return () => clearTimeout(timer);
  }, [onClose]);

  const bgColor = type === "error" ? "bg-red-500/10 border-red-500/20" : "bg-emerald-500/10 border-emerald-500/20";
  const textColor = type === "error" ? "text-red-200" : "text-emerald-200";

  return (
    <div className={`fixed bottom-4 right-4 ${bgColor} border rounded-lg p-4 shadow-lg z-50 animate-in slide-in-from-bottom-4`}>
      <div className="flex items-center gap-3">
        <span className={textColor}>{message}</span>
        <button
          onClick={onClose}
          className={`text-slate-400 hover:text-white transition-colors`}
        >
          ×
        </button>
      </div>
    </div>
  );
}
