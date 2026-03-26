import React, { useEffect, useState } from "react";
import { 
  Users, 
  ArrowRight, 
  Cpu, 
  Presentation, 
  Terminal,
  Layers,
  Sparkles,
  ChevronDown,
  Quote,
  Search,
  Zap,
  Shield,
  Activity
} from "lucide-react";

interface LandingPageProps {
  onLaunch: () => void;
  onLogin: () => void;
}

const LandingPage: React.FC<LandingPageProps> = ({ onLaunch, onLogin }) => {
  const [activeFaq, setActiveFaq] = useState<number | null>(null);

  useEffect(() => {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('active');
        }
      });
    }, { threshold: 0.1 });

    document.querySelectorAll('.reveal').forEach(el => observer.observe(el));
    return () => observer.disconnect();
  }, []);

  return (
    <div className="min-h-screen bg-[#020617] text-white selection:bg-blue-500/30 overflow-x-hidden font-sans">
      {/* Background Orbs */}
      <div className="fixed top-0 left-0 w-full h-full overflow-hidden pointer-events-none -z-10">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-blue-600/20 blur-[120px] rounded-full animate-pulse" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-indigo-600/20 blur-[120px] rounded-full animate-pulse" style={{ animationDelay: "2s" }} />
      </div>

      {/* Navbar */}
      <nav className="fixed top-0 left-0 w-full z-50 px-8 py-6 flex justify-between items-center nav-glass">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl overflow-hidden flex items-center justify-center shadow-lg shadow-blue-500/10 border border-white/10">
            <img src="/logo.png" alt="Logo" className="w-full h-full object-contain" />
          </div>
          <span className="text-2xl font-black tracking-tighter uppercase">Opscribe</span>
        </div>

        <div className="flex items-center gap-8">
          <button onClick={onLogin} className="text-sm font-semibold text-slate-400 hover:text-white transition-colors">Log in</button>
          <button 
            onClick={onLaunch}
            className="px-6 py-2.5 rounded-xl bg-white text-black font-bold text-sm hover:bg-slate-200 transition-all active:scale-95"
          >
            Get Started
          </button>
        </div>
      </nav>
      
      {/* Hero Section */}
      <section className="pt-48 pb-20 px-8 max-w-7xl mx-auto text-center relative">
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full glass border border-white/10 mb-8 animate-fade-in-up">
          <Sparkles className="w-4 h-4 text-blue-400" />
          <span className="text-xs font-bold uppercase tracking-widest text-blue-400">
            Next-Gen Infrastructure Agent
          </span>
        </div>
        
        <h1 className="text-6xl md:text-8xl font-black tracking-tighter mb-8 animate-fade-in-up leading-[0.9]" style={{ animationDelay: "0.1s" }}>
          Visualize. Understand. <br />
          <span className="bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-indigo-400 to-purple-500">
            Scale Smarter.
          </span>
        </h1>
        
        <p className="text-xl text-slate-400 max-w-2xl mx-auto mb-12 animate-fade-in-up leading-relaxed" style={{ animationDelay: "0.2s" }}>
          Opscribe turns your complex cloud infrastructure into an interactive, AI-powered knowledge map. Stop guessing, start architecting.
        </p>
        
        <div className="flex flex-wrap items-center justify-center gap-6 animate-fade-in-up" style={{ animationDelay: "0.3s" }}>
          <button 
            onClick={onLaunch}
            className="group px-10 py-5 rounded-2xl bg-gradient-to-r from-blue-600 to-indigo-700 font-bold text-lg hover:shadow-[0_0_40px_rgba(37,99,235,0.4)] transition-all flex items-center gap-2 active:scale-95"
          >
            Start Building Free
            <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
          </button>
          <button 
            onClick={onLogin}
            className="px-10 py-5 rounded-2xl glass border border-white/10 font-bold text-lg hover:bg-white/5 transition-all active:scale-95"
          >
            View Live Demo
          </button>
        </div>
      </section>

      {/* Mission Statement Section */}
      <section id="mission" className="py-32 border-y border-white/5 bg-white/[0.01] relative overflow-hidden">
        <div className="absolute inset-0 bg-blue-500/5 blur-[100px] -z-10" />
        <div className="max-w-4xl mx-auto px-8 text-center reveal">
          <h2 className="text-sm font-black uppercase tracking-[0.4em] text-blue-500 mb-8">Our Mission</h2>
          <p className="text-3xl md:text-5xl font-black italic leading-[1.1] tracking-tight text-white mb-10">
            "To bridge the gap between complex cloud architecture and human understanding, empowering engineers to build the future with absolute clarity and grounded intelligence."
          </p>
          <div className="flex justify-center items-center gap-4 text-slate-500">
            <div className="h-[1px] w-12 bg-white/10" />
             <span className="text-xs font-bold uppercase tracking-widest italic">The Opscribe Manifesto</span>
            <div className="h-[1px] w-12 bg-white/10" />
          </div>
        </div>
      </section>

      {/* Featured Bento Grid */}
      <section id="features" className="py-32 px-8 max-w-7xl mx-auto">
        <div className="text-center mb-20 reveal">
          <h2 className="text-4xl md:text-5xl font-black mb-6">Built for Modern Ops</h2>
          <p className="text-slate-400 text-lg max-w-2xl mx-auto">Complex systems made simple through state-of-the-art visualization and grounded architectural intelligence.</p>
        </div>

        <div className="bento-grid">
          {/* Main Feature: RAG Engine */}
          <div className="bento-item group bento-item-lg p-10 flex flex-col justify-between reveal border border-white/5 bg-white/[0.02] hover:bg-white/[0.05] transition-colors rounded-[2.5rem]">
            <div className="space-y-6">
              <div className="w-14 h-14 rounded-2xl bg-blue-500/10 flex items-center justify-center border border-blue-500/20 shadow-inner">
                <Cpu className="w-7 h-7 text-blue-400" />
              </div>
              <h3 className="text-3xl font-bold">Infinite Context RAG</h3>
              <p className="text-slate-400 text-lg leading-relaxed">Our proprietary engine ingests your UML, Cloud JSON, and Telemetry to provide 100% grounded architectural intelligence with zero hallucinations.</p>
            </div>
            <div className="mt-8 flex gap-3">
              <span className="px-4 py-1.5 rounded-full bg-blue-500/10 text-xs font-bold border border-blue-500/20 text-blue-400 uppercase tracking-wider">Cloud Native</span>
              <span className="px-4 py-1.5 rounded-full bg-purple-500/10 text-xs font-bold border border-purple-500/20 text-purple-400 uppercase tracking-wider">Enterprise Ready</span>
            </div>
          </div>

          <div className="bento-item group bento-item-tall p-8 flex flex-col justify-center reveal border border-white/5 bg-white/[0.02] hover:bg-white/[0.05] rounded-[2.5rem]" style={{ transitionDelay: "0.1s" }}>
            <div className="w-14 h-14 rounded-2xl bg-indigo-500/10 flex items-center justify-center border border-indigo-500/20 mb-8 shadow-inner">
              <Presentation className="w-7 h-7 text-indigo-400" />
            </div>
            <h3 className="text-2xl font-bold mb-4">Instant Documentation</h3>
            <p className="text-slate-400 leading-relaxed">Generate board-ready presentations and comprehensive system docs from your live infrastructure in seconds.</p>
          </div>

          <div className="bento-item group bento-item-md p-10 reveal border border-white/5 bg-white/[0.02] hover:bg-white/[0.05] rounded-[2.5rem]" style={{ transitionDelay: "0.2s" }}>
             <Terminal className="w-8 h-8 text-emerald-400 mb-6" />
             <h4 className="text-xl font-bold mb-2">IaC Sync</h4>
             <p className="text-slate-500 text-sm">Terraform & Pulumi auto-generation.</p>
          </div>

          {/* New Hire Experience */}
          <div className="bento-item group bento-item-md p-10 flex items-center gap-10 reveal border border-white/5 bg-white/[0.02] hover:bg-white/[0.05] rounded-[2.5rem]" style={{ transitionDelay: "0.4s" }}>
             <div className="w-24 h-24 rounded-full border border-white/10 flex items-center justify-center flex-shrink-0 relative bg-gradient-to-br from-indigo-500/10 to-blue-500/5 shadow-xl">
                <Users className="w-10 h-10 text-indigo-400" />
                <div className="absolute -top-1 -right-1 w-10 h-10 rounded-full bg-blue-500 flex items-center justify-center text-xs font-black shadow-lg shadow-blue-500/40">+10x</div>
             </div>
             <div>
               <h3 className="text-2xl font-bold mb-3">Onboard Instantly</h3>
               <p className="text-slate-400 leading-relaxed">Let new hires 'Chat with the System'. Opscribe generates interactive guides that slash onboarding time by 90%.</p>
             </div>
          </div>
        </div>
      </section>

      {/* Deep Dive Section */}
      <section id="intelligence" className="py-20 px-8 max-w-7xl mx-auto">
        <div className="grid lg:grid-cols-2 gap-24 items-center">
          <div className="reveal">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-lg bg-blue-500/10 border border-blue-500/20 mb-6">
              <Activity className="w-4 h-4 text-blue-400" />
              <span className="text-xs font-bold text-blue-400 uppercase tracking-widest text-[10px]">Real-time Analysis</span>
            </div>
            <h2 className="text-5xl font-black mb-10 leading-tight">From Messy Logs to <span className="text-blue-400">Pure Intelligence.</span></h2>
            <p className="text-xl text-slate-400 mb-10 leading-relaxed">
              Don't manually document your infrastructure. Opscribe's grounded LLM analyzes relationships and builds a living, breathing knowledge base.
            </p>
            <div className="space-y-6">
              {[
                "Identifies critical dependencies automatically",
                "Bridges the gap between PMs and Lead Architects",
                "Grounds AI responses in your actual system logic"
              ].map((text, i) => (
                <div key={i} className="flex items-center gap-4 text-slate-200 font-semibold group">
                  <div className="w-6 h-6 rounded-full bg-blue-500/20 flex items-center justify-center flex-shrink-0 group-hover:bg-blue-500 transition-colors">
                    <div className="w-1.5 h-1.5 rounded-full bg-blue-400 group-hover:bg-white" />
                  </div>
                  {text}
                </div>
              ))}
            </div>
          </div>
          <div className="relative reveal pt-20 lg:pt-0" style={{ transitionDelay: "0.2s" }}>
            <div className="w-full aspect-video glass-card p-6 flex flex-col gap-6 animate-float relative overflow-hidden group">
               <div className="absolute inset-0 bg-blue-500/5 opacity-0 group-hover:opacity-100 transition-opacity" />
               <div className="h-10 w-2/3 rounded-lg bg-white/5 animate-pulse" />
               <div className="h-6 w-full rounded-lg bg-white/5 animate-pulse" />
               <div className="flex-1 rounded-3xl bg-[#020617]/80 border border-white/10 flex items-center justify-center p-10">
                  <Layers className="w-32 h-32 text-blue-500/20 animate-pulse" />
               </div>
               <div className="h-14 w-full rounded-2xl bg-gradient-to-r from-blue-500/10 to-indigo-500/10 flex items-center px-6 border border-blue-500/10">
                  <Search className="w-5 h-5 text-blue-400 mr-4" />
                  <span className="text-sm text-blue-400 font-mono tracking-tight">system.analyze(architecture_uml.json)</span>
               </div>
            </div>
            <div className="absolute -top-12 -right-12 w-48 h-48 glass-card p-10 rotate-12 animate-float shadow-2xl border-white/20" style={{ animationDelay: "1s" }}>
               <Presentation className="w-full h-full text-indigo-400 opacity-60" />
            </div>
            <div className="absolute -bottom-10 -left-10 px-6 py-4 glass-card animate-float flex items-center gap-4" style={{ animationDelay: "1.5s" }}>
               <div className="w-4 h-4 rounded-full bg-emerald-500 animate-ping" />
               <span className="text-sm font-bold">100% Grounded</span>
            </div>
          </div>
        </div>
      </section>

      {/* Testimonials Section */}
      <section id="testimonials" className="py-20 px-8 bg-white/[0.01]">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-24 reveal">
            <h2 className="text-5xl font-black mb-6">Loved by Architects</h2>
            <p className="text-slate-400 text-xl">The intelligence layer that modern engineering teams can't live without.</p>
          </div>
          
          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                name: "Sarah Chen",
                quote: "Opscribe literally cut our cloud discovery time from weeks to seconds. It's the first tool that actually understands complex dependency chains.",
                delay: "0s"
              },
              {
                name: "Marcus Thorne",
                quote: "I can finally answer stakeholder questions about our infrastructure without having to go on a 3-day deep dive into old tickets and diagrams.",
                delay: "0.1s"
              },
              {
                name: "Elena Rodriguez",
                quote: "The slide generation is a game changer for board meetings. I just click export and everything is ready for the executive team.",
                delay: "0.2s"
              }
            ].map((t, i) => (
              <div key={i} className="testimonial-card reveal" style={{ transitionDelay: t.delay }}>
                <Quote className="w-10 h-10 text-blue-500/20 mb-4" />
                <p className="text-slate-300 text-lg italic leading-relaxed mb-8 flex-1">"{t.quote}"</p>
                <div className="flex items-center gap-4 border-t border-white/5 pt-6">
                  <div className="avatar flex items-center justify-center font-black text-xs text-slate-500">{t.name[0]}</div>
                  <div>
                    <h4 className="font-bold text-white">{t.name}</h4>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section id="faq" className="py-20 px-8 max-w-3xl mx-auto">
        <div className="text-center mb-20 reveal">
          <h2 className="text-5xl font-black mb-6">Common Questions</h2>
          <p className="text-slate-400 text-xl">Everything you need to know about architectural intelligence.</p>
        </div>
        
        <div className="space-y-4">
          {[
            {
              q: "How does Opscribe protect our sensitive cloud data?",
              a: "We use SOC2-compliant data isolation. Your cloud manifest data is encrypted at rest and in transit, and our LLM is grounded in a private context window that never leaks to other clients."
            },
            {
              q: "Does Opscribe require a 24/7 connection to our cloud?",
              a: "No. You can run one-off discoveries or schedule weekly syncs. We also support manual JSON/UML uploads for teams with strict air-gapped requirements."
            },
            {
              q: "Can I use Opscribe to auto-generate Terraform files?",
              a: "Yes. Our IaC Sync engine analyzes your logical graph and can generate fully documented Terraform, Pulumi, or K8s manifests directly."
            }
          ].map((f, i) => (
            <div key={i} className="faq-item reveal group cursor-pointer" onClick={() => setActiveFaq(activeFaq === i ? null : i)}>
              <div className="flex justify-between items-center gap-8 py-2">
                <h4 className="text-xl font-bold group-hover:text-blue-400 transition-colors">{f.q}</h4>
                <ChevronDown className={`w-6 h-6 text-slate-500 transition-transform duration-300 ${activeFaq === i ? 'rotate-180 text-blue-400' : ''}`} />
              </div>
              {activeFaq === i && (
                <p className="text-slate-400 mt-4 leading-relaxed animate-fade-in-up">{f.a}</p>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="py-32 px-8 border-t border-white/5 bg-[#010309] relative">
        <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-4 gap-20">
          <div className="col-span-1 md:col-span-1">
            <div className="flex items-center gap-3 mb-8">
              <div className="w-10 h-10 rounded-xl overflow-hidden flex items-center justify-center">
                <img src="/logo.png" alt="Logo" className="w-full h-full object-contain" />
              </div>
              <span className="text-2xl font-black tracking-tighter uppercase">Opscribe</span>
            </div>
            <p className="text-slate-500 leading-relaxed mb-8">The first LLM-powered intelligence layer for enterprise infrastructure. Map, understand, and scale your cloud without the headache.</p>
            <div className="flex gap-4">
               <div className="w-10 h-10 rounded-full border border-white/10 flex items-center justify-center hover:bg-white/5 transition-colors cursor-pointer text-slate-500 hover:text-white"><Zap className="w-5 h-5" /></div>
               <div className="w-10 h-10 rounded-full border border-white/10 flex items-center justify-center hover:bg-white/5 transition-colors cursor-pointer text-slate-500 hover:text-white"><Layers className="w-5 h-5" /></div>
            </div>
          </div>
          
          <div>
            <h5 className="font-black uppercase tracking-widest text-xs text-white mb-8">Product</h5>
            <ul className="space-y-4 text-sm font-bold text-slate-500 uppercase tracking-widest">
              <li><a href="#" className="hover:text-blue-400 transition-colors italic">Agentic Dashboard</a></li>
              <li><a href="#" className="hover:text-blue-400 transition-colors italic">RAG Intelligence</a></li>
              <li><a href="#" className="hover:text-blue-400 transition-colors italic">Slide Export</a></li>
              <li><a href="#" className="hover:text-blue-400 transition-colors italic">IaC Sync</a></li>
            </ul>
          </div>

          <div>
            <h5 className="font-black uppercase tracking-widest text-xs text-white mb-8">Resources</h5>
            <ul className="space-y-4 text-sm font-bold text-slate-500 uppercase tracking-widest">
              <li><a href="#" className="hover:text-blue-400 transition-colors italic">Documentation</a></li>
              <li><a href="#" className="hover:text-blue-400 transition-colors italic">API Reference</a></li>
              <li><a href="#" className="hover:text-blue-400 transition-colors italic">Cloud Status</a></li>
              <li><a href="#" className="hover:text-blue-400 transition-colors italic">Security Library</a></li>
            </ul>
          </div>

          <div>
            <h5 className="font-black uppercase tracking-widest text-xs text-white mb-8">Company</h5>
            <ul className="space-y-4 text-sm font-bold text-slate-500 uppercase tracking-widest">
              <li><a href="#" className="hover:text-blue-400 transition-colors italic">About Us</a></li>
              <li><a href="#" className="hover:text-blue-400 transition-colors italic">Careers</a></li>
              <li><a href="#" className="hover:text-blue-400 transition-colors italic">Blog</a></li>
              <li><a href="#" className="hover:text-blue-400 transition-colors italic">Privacy Policy</a></li>
            </ul>
          </div>
        </div>
        
        <div className="max-w-7xl mx-auto border-t border-white/5 mt-32 pt-12 flex flex-col md:flex-row justify-between items-center gap-8">
           <div className="text-slate-600 text-[10px] uppercase font-black tracking-[0.4em]">© 2026 Opscribe Inc. Engineered in the future.</div>
           <div className="flex gap-8 text-[10px] uppercase font-black tracking-widest text-slate-600">
             <a href="#" className="hover:text-white">Twitter</a>
             <a href="#" className="hover:text-white">Discord</a>
             <a href="#" className="hover:text-white">LinkedIn</a>
           </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
