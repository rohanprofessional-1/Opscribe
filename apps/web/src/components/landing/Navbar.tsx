import React from "react";

interface NavbarProps {
  onNavigate: (view: "LANDING" | "ENTERPRISE" | "DASHBOARD") => void;
  currentView: string;
}

const Navbar: React.FC<NavbarProps> = ({ onNavigate, currentView }) => {
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 h-20 flex items-center justify-between px-8 glass border-b border-white/10">
      <div 
        className="flex items-center gap-3 cursor-pointer group" 
        onClick={() => onNavigate("LANDING")}
      >
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-400 to-indigo-600 p-0.5 group-hover:scale-110 transition-transform duration-300">
           <img src="/assets/logo.png" alt="Opscribe Logo" className="w-full h-full object-contain rounded-[10px]" />
        </div>
        <span className="text-2xl font-bold tracking-tight neon-text">
          Opscribe
        </span>
      </div>

      <div className="hidden md:flex items-center gap-10">
        <button 
          onClick={() => onNavigate("LANDING")}
          className={`text-sm font-medium transition-colors hover:text-cyan-400 ${currentView === "LANDING" ? "text-cyan-400" : "text-slate-300"}`}
        >
          Product
        </button>
        <button 
          className="text-sm font-medium text-slate-300 hover:text-cyan-400 transition-colors"
        >
          Solutions
        </button>
        <button 
           onClick={() => onNavigate("ENTERPRISE")}
          className={`text-sm font-medium transition-colors hover:text-cyan-400 ${currentView === "ENTERPRISE" ? "text-cyan-400" : "text-slate-300"}`}
        >
          Enterprise
        </button>
      </div>

      <div className="flex items-center gap-4">
        <button 
          onClick={() => onNavigate("DASHBOARD")}
          className="px-6 py-2.5 rounded-full text-sm font-semibold bg-white/10 hover:bg-white/20 border border-white/10 transition-all active:scale-95"
        >
          Sign In
        </button>
        <button 
          onClick={() => onNavigate("DASHBOARD")}
          className="px-6 py-2.5 rounded-full text-sm font-semibold bg-gradient-to-r from-cyan-500 to-indigo-600 hover:shadow-[0_0_20px_rgba(0,242,255,0.3)] transition-all active:scale-95"
        >
          Launch App
        </button>
      </div>
    </nav>
  );
};

export default Navbar;
