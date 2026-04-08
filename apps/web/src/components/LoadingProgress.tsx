import { Zap, Loader2 } from "lucide-react";

interface LoadingProgressProps {
  isVisible: boolean;
  graphName: string;
}

export default function LoadingProgress({ isVisible, graphName }: LoadingProgressProps) {
  if (!isVisible) return null;

  return (
    <div className="fixed bottom-0 left-0 w-full z-[100] bg-[#020617]/90 backdrop-blur-xl border-t border-blue-500/20 shadow-[0_-10px_40px_rgba(59,130,246,0.15)] animate-in slide-in-from-bottom-full duration-500">
      <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between gap-8">
        <div className="flex items-center gap-4 shrink-0">
          <div className="w-10 h-10 rounded-xl bg-blue-600/20 flex items-center justify-center relative overflow-hidden group">
            <Zap className="w-5 h-5 text-blue-400 relative z-10 animate-pulse" />
            <div className="absolute inset-0 bg-blue-500/20 blur-xl opacity-50 group-hover:opacity-100 transition-opacity" />
          </div>
          <div>
            <h4 className="text-sm font-bold text-white tracking-tight flex items-center gap-2">
              Ingesting Infrastructure: <span className="text-blue-400">"{graphName}"</span>
            </h4>
            <div className="flex items-center gap-2 mt-1">
                <Loader2 className="w-3 h-3 text-blue-500 animate-spin" />
                <p className="text-[10px] text-gray-500 uppercase tracking-widest font-bold">Discovering resources & building map...</p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 pr-4">
          <div className="flex flex-col items-end">
             <span className="text-[10px] font-mono text-blue-500 font-bold uppercase tracking-widest">Processing</span>
             <p className="text-[10px] text-gray-500 font-medium">Please wait...</p>
          </div>
          <div className="w-8 h-8 rounded-full border-2 border-blue-500/20 border-t-blue-500 animate-spin" />
        </div>
      </div>
      
      {/* CSS for Shimmer Animation */}
      <style>{`
        @keyframes shimmer {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(100%); }
        }
        .animate-shimmer {
          animation: shimmer 2s infinite linear;
        }
      `}</style>
    </div>
  );
}
