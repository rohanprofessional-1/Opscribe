import React, { useState } from "react";
import { Mail, Lock, ArrowRight, Github } from "lucide-react";

interface LoginPageProps {
  onLogin: () => void;
  onBackToLanding: () => void;
  onGoToSignup: () => void;
}

const LoginPage: React.FC<LoginPageProps> = ({ onLogin, onBackToLanding, onGoToSignup }) => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    // Fake login delay
    setTimeout(() => {
      setIsLoading(false);
      onLogin();
    }, 1000);
  };

  return (
    <div className="min-h-screen bg-[#020617] text-white flex flex-col justify-center items-center p-6 relative overflow-hidden font-sans">
      {/* Background Orbs */}
      <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-blue-600/10 blur-[120px] rounded-full" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-indigo-600/10 blur-[120px] rounded-full" />

      <button 
        onClick={onBackToLanding}
        className="absolute top-8 left-8 flex items-center gap-2 text-slate-400 hover:text-white transition-colors group"
      >
        <div className="w-8 h-8 rounded-lg overflow-hidden flex items-center justify-center bg-white/5 group-hover:bg-white/10 transition-colors">
          <img src="/logo.png" alt="Logo" className="w-5 h-5 object-contain" />
        </div>
        <span className="text-sm font-bold uppercase tracking-widest">Opscribe</span>
      </button>

      <div className="w-full max-w-md">
        <div className="glass-card p-10 border-white/10 bg-white/[0.02] rounded-[2.5rem] shadow-2xl relative overflow-hidden text-center">
          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-blue-500 to-indigo-600" />
          
          <div className="w-16 h-16 rounded-2xl mx-auto mb-6 overflow-hidden flex items-center justify-center bg-white/5 border border-white/10">
            <img src="/logo.png" alt="Logo" className="w-10 h-10 object-contain" />
          </div>
            <h1 className="text-4xl font-black tracking-tighter mb-3 uppercase">Welcome Back</h1>
            <p className="text-slate-400 font-medium">Elevate your infrastructure intelligence.</p>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-2">
              <label className="text-xs font-black uppercase tracking-widest text-slate-500 ml-1">Email Address</label>
              <div className="relative group">
                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500 group-focus-within:text-blue-400 transition-colors" />
                <input 
                  type="email" 
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full bg-[#030816] border border-white/10 rounded-2xl py-4 pl-12 pr-4 text-white placeholder:text-slate-600 focus:outline-none focus:border-blue-500/50 focus:ring-4 focus:ring-blue-500/10 transition-all"
                  placeholder="name@company.com"
                  required
                />
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex justify-between items-center ml-1">
                <label className="text-xs font-black uppercase tracking-widest text-slate-500">Password</label>
                <a href="#" className="text-[10px] font-black uppercase tracking-widest text-blue-400 hover:text-blue-300 transition-colors">Forgot?</a>
              </div>
              <div className="relative group">
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500 group-focus-within:text-blue-400 transition-colors" />
                <input 
                  type="password" 
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-[#030816] border border-white/10 rounded-2xl py-4 pl-12 pr-4 text-white placeholder:text-slate-600 focus:outline-none focus:border-blue-500/50 focus:ring-4 focus:ring-blue-500/10 transition-all"
                  placeholder="••••••••"
                  required
                />
              </div>
            </div>

            <button 
              type="submit"
              disabled={isLoading}
              className="w-full bg-white text-black font-black py-4 rounded-2xl hover:bg-slate-200 transition-all active:scale-[0.98] flex items-center justify-center gap-2 shadow-xl shadow-white/5 disabled:opacity-50"
            >
              {isLoading ? (
                <div className="w-5 h-5 border-2 border-black/20 border-t-black rounded-full animate-spin" />
              ) : (
                <>
                  SIGN IN TO DASHBOARD
                  <ArrowRight className="w-5 h-5" />
                </>
              )}
            </button>
          </form>

          <div className="mt-8 relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-white/10"></div>
            </div>
            <div className="relative flex justify-center text-xs uppercase font-black tracking-widest">
              <span className="bg-[#0b101f] px-4 text-slate-500">Or continue with</span>
            </div>
          </div>

          <div className="mt-8">
            <button className="w-full bg-white/5 border border-white/10 text-white font-bold py-4 rounded-2xl hover:bg-white/10 transition-all active:scale-[0.98] flex items-center justify-center gap-3">
              <Github className="w-5 h-5" />
              Github Enterprise
            </button>
          </div>
        </div>

        <p className="mt-8 text-center text-slate-500 text-sm font-medium">
          Don't have an account?{" "}
          <button 
            onClick={onGoToSignup}
            className="text-blue-400 font-bold hover:text-blue-300 transition-colors underline underline-offset-4 decoration-blue-400/30"
          >
            Create account
          </button>
        </p>
      </div>
    </div>
  );
};

export default LoginPage;
