import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Rocket, Shield, Zap } from 'lucide-react';

const LandingPage: React.FC = () => {
    const navigate = useNavigate();

    return (
        <div className="min-h-screen bg-slate-900 text-white flex flex-col items-center justify-center p-6 text-center">
            <div className="absolute top-0 left-0 w-full h-full overflow-hidden z-0 pointer-events-none">
                <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-blue-600/20 blur-[120px] rounded-full"></div>
                <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-purple-600/20 blur-[120px] rounded-full"></div>
            </div>

            <div className="relative z-10 max-w-4xl mx-auto">
                <h1 className="text-6xl font-bold mb-6 bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
                    Opscribe Infrastructure Designer
                </h1>
                <p className="text-xl text-slate-400 mb-10 max-w-2xl mx-auto">
                    Design, visualize, and manage your cloud infrastructure with precision and style.
                    Built for teams that demand excellence.
                </p>

                <div className="flex gap-4 justify-center mb-16">
                    <button
                        onClick={() => navigate('/setup')}
                        className="px-8 py-4 bg-blue-600 hover:bg-blue-500 rounded-lg font-semibold transition-all shadow-lg shadow-blue-900/40"
                    >
                        Get Started
                    </button>
                    <button
                        onClick={() => navigate('/login')}
                        className="px-8 py-4 bg-slate-800 hover:bg-slate-700 rounded-lg font-semibold transition-all border border-slate-700"
                    >
                        Sign In
                    </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-8 text-left">
                    <div className="p-6 bg-slate-800/50 rounded-2xl border border-slate-700 backdrop-blur-sm">
                        <Zap className="text-blue-400 mb-4" size={32} />
                        <h3 className="text-xl font-bold mb-2">Lightning Fast</h3>
                        <p className="text-slate-400">Collaborative design in real-time with zero lag.</p>
                    </div>
                    <div className="p-6 bg-slate-800/50 rounded-2xl border border-slate-700 backdrop-blur-sm">
                        <Shield className="text-purple-400 mb-4" size={32} />
                        <h3 className="text-xl font-bold mb-2">Enterprise Ready</h3>
                        <p className="text-slate-400">Secure SSO login and granular permissions.</p>
                    </div>
                    <div className="p-6 bg-slate-800/50 rounded-2xl border border-slate-700 backdrop-blur-sm">
                        <Rocket className="text-green-400 mb-4" size={32} />
                        <h3 className="text-xl font-bold mb-2">Visual Mapping</h3>
                        <p className="text-slate-400">Auto-discover and visualize your entire stack.</p>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default LandingPage;
