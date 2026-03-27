import React, { useState } from "react";
import { 
  Calendar, 
  Settings, 
  ShieldCheck, 
  CircleCheck, 
  ArrowRight
} from "lucide-react";

interface EnterpriseSetupProps {
  onBack: () => void;
}

const EnterpriseSetup: React.FC<EnterpriseSetupProps> = ({ onBack }) => {
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitted(true);
  };

  return (
    <div className="min-h-screen bg-[#050a14] pt-32 pb-20 px-8">
      <div className="hero-glow" />
      
      <div className="max-w-6xl mx-auto flex flex-col lg:flex-row gap-16 items-start">
        {/* Left Side: Copy */}
        <div className="lg:w-1/2 animate-fade-in-up">
          <button 
            onClick={onBack}
            className="text-sm font-semibold text-cyan-400 mb-8 hover:underline flex items-center gap-2"
          >
            <ArrowRight className="w-4 h-4 rotate-180" />
            Back to Home
          </button>
          
          <h1 className="text-5xl font-black tracking-tight mb-8">
            Opscribe <span className="gradient-text">Enterprise</span> <br />
            Setup & Consultation
          </h1>
          
          <p className="text-lg text-slate-400 mb-12 leading-relaxed">
            Configure your enterprise-grade agentic environment. Our senior architects will assist in mapping your existing infrastructure and safely transitioning to agentic operations.
          </p>

          <div className="space-y-8">
            <InfoItem 
              icon={<ShieldCheck className="w-6 h-6 text-emerald-400" />}
              title="SOC2 & Security Compliant"
              description="Enterprise-grade security and data isolation for your most sensitive infrastructure data."
            />
            <InfoItem 
              icon={<Calendar className="w-6 h-6 text-indigo-400" />}
              title="Dedicated Support"
              description="Direct access to our core architecture team during the entire rollout phase."
            />
            <InfoItem 
              icon={<Settings className="w-6 h-6 text-cyan-400" />}
              title="Custom Integrations"
              description="Tailored connectors for your specific stack, whether on-prem or multi-cloud."
            />
          </div>
        </div>

        {/* Right Side: Form */}
        <div className="lg:w-1/2 w-full animate-fade-in-up" style={{ animationDelay: "0.2s" }}>
          <div className="glass-card p-10 relative overflow-hidden">
             {submitted ? (
               <div className="py-20 text-center animate-fade-in-up">
                 <div className="w-20 h-20 bg-emerald-500/10 rounded-full flex items-center justify-center mx-auto mb-8 neon-border">
                    <CircleCheck className="w-10 h-10 text-emerald-400" />
                 </div>
                 <h2 className="text-3xl font-bold mb-4">Request Received</h2>
                 <p className="text-slate-400 mb-8">
                   A senior Opscribe architect will contact you within 2 business hours to schedule your consultation.
                 </p>
                 <button 
                    onClick={onBack}
                    className="px-8 py-3 rounded-xl bg-white/10 hover:bg-white/20 transition-all"
                  >
                    Return Home
                  </button>
               </div>
             ) : (
               <>
                 <h2 className="text-2xl font-bold mb-8">Book a Consultation</h2>
                 <form onSubmit={handleSubmit} className="space-y-6">
                    <div className="space-y-2">
                       <label className="text-sm font-semibold text-slate-400">Full Name</label>
                       <input 
                         required
                         type="text" 
                         placeholder="John Doe" 
                         className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl focus:outline-none focus:border-cyan-400 transition-colors"
                       />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                       <div className="space-y-2">
                          <label className="text-sm font-semibold text-slate-400">Work Email</label>
                          <input 
                            required
                            type="email" 
                            placeholder="john@company.com" 
                            className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl focus:outline-none focus:border-cyan-400 transition-colors"
                          />
                       </div>
                       <div className="space-y-2">
                          <label className="text-sm font-semibold text-slate-400">Company Size</label>
                          <select className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl focus:outline-none focus:border-cyan-400 transition-colors cursor-pointer appearance-none">
                             <option className="bg-[#050a14]">50-200 employees</option>
                             <option className="bg-[#050a14]">200-1000 employees</option>
                             <option className="bg-[#050a14]">1000+ employees</option>
                          </select>
                       </div>
                    </div>
                    <div className="space-y-2">
                       <label className="text-sm font-semibold text-slate-400">Primary Cloud Focus</label>
                       <div className="flex gap-4">
                          <label className="flex-1 flex items-center gap-2 p-4 rounded-xl border border-white/10 cursor-pointer hover:bg-white/5 transition-colors">
                             <input type="radio" name="cloud" className="accent-cyan-400" />
                             AWS
                          </label>
                          <label className="flex-1 flex items-center gap-2 p-4 rounded-xl border border-white/10 cursor-pointer hover:bg-white/5 transition-colors">
                             <input type="radio" name="cloud" className="accent-cyan-400" />
                             Azure
                          </label>
                          <label className="flex-1 flex items-center gap-2 p-4 rounded-xl border border-white/10 cursor-pointer hover:bg-white/5 transition-colors">
                             <input type="radio" name="cloud" className="accent-cyan-400" />
                             GCP
                          </label>
                       </div>
                    </div>
                    <div className="space-y-2">
                       <label className="text-sm font-semibold text-slate-400">Notes (Optional)</label>
                       <textarea 
                         placeholder="Tell us about your infrastructure goals..."
                         className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl focus:outline-none focus:border-cyan-400 transition-colors h-32"
                       />
                    </div>
                    <button 
                      type="submit"
                      className="w-full py-4 rounded-xl bg-gradient-to-r from-cyan-500 to-indigo-600 font-bold text-lg hover:shadow-[0_0_20px_rgba(0,242,255,0.3)] transition-all active:scale-95"
                    >
                      Request Enterprise Consultation
                    </button>
                 </form>
               </>
             )}
          </div>
        </div>
      </div>
    </div>
  );
};

const InfoItem = ({ icon, title, description }: { icon: React.ReactNode; title: string; description: string }) => (
  <div className="flex items-start gap-6">
    <div className="w-12 h-12 rounded-2xl bg-white/5 flex items-center justify-center flex-shrink-0 neon-border">
      {icon}
    </div>
    <div>
      <h3 className="text-lg font-bold mb-1">{title}</h3>
      <p className="text-slate-400 text-sm leading-relaxed">{description}</p>
    </div>
  </div>
);

export default EnterpriseSetup;
