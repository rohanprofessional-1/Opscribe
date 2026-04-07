import { useState, useEffect } from "react";
import { 
    Zap, 
    Database, 
    Github, 
    X, 
    ArrowRight, 
    CheckCircle, 
    AlertCircle, 
    Network,
    Globe
} from "lucide-react";
import { authFetch as fetch } from "../api/client";

const API_BASE = "/api";

interface IngestionWizardProps {
    isOpen: boolean;
    onClose: () => void;
    clientId: string;
    onIngestionStarted: (graphName: string) => void;
}

export default function IngestionWizard({ isOpen, onClose, clientId, onIngestionStarted }: IngestionWizardProps) {
    const [step, setStep] = useState(1);
    const [graphName, setGraphName] = useState("");
    const [connectionInstructions, setConnectionInstructions] = useState("");
    const [includeAws, setIncludeAws] = useState(true);
    const [awsRegion, setAwsRegion] = useState("us-east-1");
    const [includeGithub, setIncludeGithub] = useState(true);
    const [selectedRepos, setSelectedRepos] = useState<string[]>([]);
    const [availableRepos, setAvailableRepos] = useState<any[]>([]);
    const [loadingRepos, setLoadingRepos] = useState(false);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (isOpen && clientId) {
            fetchAvailableRepos();
        }
    }, [isOpen, clientId]);

    const fetchAvailableRepos = async () => {
        setLoadingRepos(true);
        try {
            // Fetch ALL authorized repositories from the GitHub App installation,
            // not just the ones that have been "pre-connected" in Settings.
            const res = await fetch(`${API_BASE}/github/repos?client_id=${clientId}`);
            if (res.ok) {
                const data = await res.json();
                setAvailableRepos(data);
                // Auto-select all by default
                setSelectedRepos(data.map((r: any) => `https://github.com/${r.name}`));
            }
        } catch (err) {
            console.error("Failed to fetch available repos", err);
        } finally {
            setLoadingRepos(false);
        }
    };

    const handleStartIngestion = async () => {
        if (!graphName) {
            setError("Please provide a name for your graph.");
            return;
        }

        setIsSubmitting(true);
        setError(null);

        try {
            const res = await fetch(`${API_BASE}/pipeline/export`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    client_id: clientId,
                    include_aws: includeAws,
                    include_github: includeGithub,
                    aws_region: awsRegion,
                    graph_name: graphName,
                    instructions: connectionInstructions,
                    repositories: includeGithub ? availableRepos
                        .filter(r => selectedRepos.includes(`https://github.com/${r.name}`))
                        .map(r => ({
                            repo_url: `https://github.com/${r.name}`,
                            target_repo_id: r.id.toString(),
                            default_branch: r.default_branch
                        })) : []
                })
            });

            if (!res.ok) {
                const data = await res.json();
                throw new Error(data.detail || "Failed to start ingestion");
            }

            onIngestionStarted(graphName);
            onClose();
        } catch (err: any) {
            setError(err.message);
        } finally {
            setIsSubmitting(false);
        }
    };

    const toggleRepo = (repoUrl: string) => {
        setSelectedRepos(prev => 
            prev.includes(repoUrl) 
                ? prev.filter(url => url !== repoUrl) 
                : [...prev, repoUrl]
        );
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black/90 backdrop-blur-sm z-[60] flex items-center justify-center p-4">
            <div className="bg-[#0f172a] border border-blue-500/30 rounded-2xl w-full max-w-xl overflow-hidden flex flex-col shadow-2xl shadow-blue-500/10">
                
                {/* Header */}
                <div className="px-8 py-6 border-b border-white/5 flex justify-between items-center bg-gradient-to-r from-blue-600/10 to-purple-600/10">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
                            <Zap className="w-5 h-5 text-white" />
                        </div>
                        <div>
                            <h2 className="text-xl font-bold text-white tracking-tight">New Infrastructure Ingestion</h2>
                            <p className="text-xs text-blue-400 font-medium uppercase tracking-wider">Step {step} of 3</p>
                        </div>
                    </div>
                    <button onClick={onClose} className="text-gray-400 hover:text-white p-2 hover:bg-white/5 rounded-full transition-colors">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Progress Bar */}
                <div className="w-full h-1 bg-gray-800">
                    <div 
                        className="h-full bg-blue-500 transition-all duration-300" 
                        style={{ width: `${(step / 3) * 100}%` }}
                    />
                </div>

                {/* Content */}
                <div className="p-8 flex-1 overflow-y-auto max-h-[60vh]">
                    {step === 1 && (
                        <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-300">
                            <div>
                                <h3 className="text-lg font-semibold text-white mb-2">Identify your Graph</h3>
                                <p className="text-sm text-gray-400 mb-6">Give your architectural map a name to differentiate it from other environments.</p>
                                
                                <div className="space-y-4">
                                    <div className="space-y-2">
                                        <label className="text-xs font-semibold text-gray-500 uppercase tracking-widest ml-1">Connection Instructions</label>
                                        <textarea 
                                            value={connectionInstructions}
                                            onChange={(e) => setConnectionInstructions(e.target.value)}
                                            placeholder="e.g. Map my us-east-1 VPC and the 'frontend' repository..."
                                            className="w-full bg-[#1e293b] border border-gray-700/50 rounded-xl py-3 px-4 text-white placeholder-gray-600 focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 outline-none transition-all min-h-[100px] text-sm"
                                            autoFocus
                                        />
                                    </div>

                                    <div className="space-y-2">
                                        <label className="text-xs font-semibold text-gray-500 uppercase tracking-widest ml-1">Graph Name</label>
                                        <div className="relative group">
                                            <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                                                <Network className="w-5 h-5 text-gray-500 group-focus-within:text-blue-500 transition-colors" />
                                            </div>
                                            <input 
                                                type="text" 
                                                value={graphName}
                                                onChange={(e) => setGraphName(e.target.value)}
                                                placeholder="e.g. Production Stack - Q2"
                                                className="w-full bg-[#1e293b] border border-gray-700/50 rounded-xl py-4 pl-12 pr-4 text-white placeholder-gray-600 focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 outline-none transition-all"
                                            />
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div className="bg-blue-500/5 border border-blue-500/10 rounded-xl p-4 flex gap-4">
                                <div className="w-10 h-10 rounded-full bg-blue-500/10 flex items-center justify-center shrink-0">
                                    <AlertCircle className="w-5 h-5 text-blue-400" />
                                </div>
                                <p className="text-sm text-gray-400 leading-relaxed">
                                    This name will be shown on your dashboard. You can create multiple graphs from the same cloud and code sources.
                                </p>
                            </div>
                        </div>
                    )}

                    {step === 2 && (
                        <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-300">
                            <div>
                                <h3 className="text-lg font-semibold text-white mb-2">Cloud Infrastructure</h3>
                                <p className="text-sm text-gray-400 mb-6">Select the AWS environment to discover during this ingestion.</p>
                                
                                <div className="space-y-4">
                                    <button 
                                        onClick={() => setIncludeAws(!includeAws)}
                                        className={`w-full flex items-center justify-between p-4 rounded-xl border transition-all ${includeAws ? 'bg-blue-600/10 border-blue-500/50 text-white' : 'bg-gray-800/50 border-gray-700 text-gray-500'}`}
                                    >
                                        <div className="flex items-center gap-3">
                                            <Database className={`w-5 h-5 ${includeAws ? 'text-blue-400' : 'text-gray-600'}`} />
                                            <span className="font-medium">Amazon Web Services (AWS)</span>
                                        </div>
                                        <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center transition-colors ${includeAws ? 'bg-blue-500 border-blue-500' : 'border-gray-600'}`}>
                                            {includeAws && <CheckCircle className="w-4 h-4 text-white" />}
                                        </div>
                                    </button>

                                    {includeAws && (
                                        <div className="pl-6 space-y-3 animate-in slide-in-from-top-2 duration-200">
                                            <label className="text-xs font-semibold text-gray-500 uppercase tracking-widest">Discovery Region</label>
                                            <div className="grid grid-cols-2 gap-3">
                                                {['us-east-1', 'us-west-2', 'eu-west-1', 'ap-southeast-1'].map(region => (
                                                    <button 
                                                        key={region}
                                                        onClick={() => setAwsRegion(region)}
                                                        className={`flex items-center justify-center gap-2 py-2.5 rounded-lg border text-sm transition-all ${awsRegion === region ? 'bg-blue-500/20 border-blue-500 text-blue-300 shadow-[0_0_15px_rgba(59,130,246,0.1)]' : 'bg-gray-800/30 border-gray-700 text-gray-500 hover:border-gray-600'}`}
                                                    >
                                                        <Globe className="w-3.5 h-3.5" />
                                                        {region}
                                                    </button>
                                                ))}
                                                <div className="col-span-2 relative">
                                                    <input 
                                                        type="text" 
                                                        value={awsRegion}
                                                        onChange={(e) => setAwsRegion(e.target.value)}
                                                        placeholder="custom-region-1"
                                                        className="w-full bg-[#1e293b] border border-gray-700/50 rounded-lg py-2 px-3 text-sm text-white focus:ring-1 focus:ring-blue-500 outline-none"
                                                    />
                                                </div>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    )}

                    {step === 3 && (
                        <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-300">
                            <div>
                                <h3 className="text-lg font-semibold text-white mb-2">Codebase Selection</h3>
                                <p className="text-sm text-gray-400 mb-6">Choose the connected repositories to link with your cloud infrastructure.</p>
                                
                                <div className="space-y-4">
                                    <button 
                                        onClick={() => setIncludeGithub(!includeGithub)}
                                        className={`w-full flex items-center justify-between p-4 rounded-xl border transition-all ${includeGithub ? 'bg-purple-600/10 border-purple-500/50 text-white' : 'bg-gray-800/50 border-gray-700 text-gray-500'}`}
                                    >
                                        <div className="flex items-center gap-3">
                                            <Github className={`w-5 h-5 ${includeGithub ? 'text-purple-400' : 'text-gray-600'}`} />
                                            <span className="font-medium">GitHub Repositories</span>
                                        </div>
                                        <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center transition-colors ${includeGithub ? 'bg-purple-500 border-purple-500' : 'border-gray-600'}`}>
                                            {includeGithub && <CheckCircle className="w-4 h-4 text-white" />}
                                        </div>
                                    </button>

                                    {includeGithub && (
                                        <div className="pl-2 space-y-2 animate-in slide-in-from-top-2 duration-200">
                                            {loadingRepos ? (
                                                <p className="text-center py-4 text-xs text-gray-500 animate-pulse">Loading available repositories...</p>
                                            ) : availableRepos.length === 0 ? (
                                                <div className="bg-gray-800/30 rounded-xl p-6 text-center border border-dashed border-gray-700">
                                                    <p className="text-sm text-gray-500 mb-2">No repositories found.</p>
                                                    <p className="text-xs text-gray-600">Ensure the Opscribe GitHub App is installed in Provider Settings.</p>
                                                </div>
                                            ) : (
                                                <div className="grid grid-cols-1 gap-2 max-h-48 overflow-y-auto pr-2 custom-scrollbar">
                                                    {availableRepos.map(repo => {
                                                        const repoUrl = `https://github.com/${repo.name}`;
                                                        return (
                                                            <button 
                                                                key={repo.id}
                                                                onClick={() => toggleRepo(repoUrl)}
                                                                className={`flex items-center gap-3 p-3 rounded-lg border text-left transition-all ${selectedRepos.includes(repoUrl) ? 'bg-white/5 border-white/20' : 'bg-transparent border-transparent opacity-50 hover:opacity-80'}`}
                                                            >
                                                                <div className={`w-4 h-4 rounded border flex items-center justify-center transition-colors ${selectedRepos.includes(repoUrl) ? 'bg-blue-500 border-blue-500' : 'border-gray-600'}`}>
                                                                    {selectedRepos.includes(repoUrl) && <CheckCircle className="w-3 h-3 text-white" />}
                                                                </div>
                                                                <div className="flex-1 min-w-0">
                                                                    <p className="text-sm font-medium text-gray-200 truncate">{repo.name}</p>
                                                                    <p className="text-[10px] text-gray-500 uppercase tracking-wider">{repo.default_branch}</p>
                                                                </div>
                                                            </button>
                                                        );
                                                    })}
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    )}

                    {error && (
                        <div className="mt-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-start gap-3 animate-shake">
                            <AlertCircle className="w-5 h-5 shrink-0" />
                            <p>{error}</p>
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="px-8 py-6 border-t border-white/5 flex justify-between items-center bg-gray-900/50">
                    <button 
                        onClick={() => step > 1 ? setStep(step - 1) : onClose()}
                        className="text-sm font-medium text-gray-500 hover:text-white transition-colors"
                    >
                        {step === 1 ? 'Cancel' : 'Previous Step'}
                    </button>
                    
                    {step < 3 ? (
                        <button 
                            onClick={() => setStep(step + 1)}
                            disabled={step === 1 && !graphName}
                            className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-800 disabled:text-gray-600 text-white px-8 py-3 rounded-xl text-sm font-bold flex items-center gap-2 transition-all shadow-lg shadow-blue-600/10 active:scale-95"
                        >
                            Next Step
                            <ArrowRight className="w-4 h-4" />
                        </button>
                    ) : (
                        <button 
                            onClick={handleStartIngestion}
                            disabled={isSubmitting || (!includeAws && !includeGithub) || (includeGithub && selectedRepos.length === 0)}
                            className="bg-green-600 hover:bg-green-500 disabled:bg-gray-800 disabled:text-gray-600 text-white px-8 py-3 rounded-xl text-sm font-bold flex items-center gap-2 transition-all shadow-lg shadow-green-600/10 active:scale-95 animate-pulse-subtle"
                        >
                            {isSubmitting ? 'Starting Ingestion...' : 'Start Discovery'}
                            <Zap className="w-4 h-4 fill-current" />
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}

// Add simple CSS for custom scrollbar and shake animation
const style = document.createElement('style');
style.textContent = `
    .custom-scrollbar::-webkit-scrollbar {
        width: 4px;
    }
    .custom-scrollbar::-webkit-scrollbar-track {
        background: transparent;
    }
    .custom-scrollbar::-webkit-scrollbar-thumb {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 10px;
    }
    .custom-scrollbar::-webkit-scrollbar-thumb:hover {
        background: rgba(255, 255, 255, 0.2);
    }
    @keyframes shake {
        0%, 100% { transform: translateX(0); }
        25% { transform: translateX(-4px); }
        75% { transform: translateX(4px); }
    }
    .animate-shake {
        animation: shake 0.2s ease-in-out 0s 2;
    }
    @keyframes pulse-subtle {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.95; transform: scale(0.99); }
    }
    .animate-pulse-subtle {
        animation: pulse-subtle 3s infinite ease-in-out;
    }
`;
document.head.appendChild(style);
