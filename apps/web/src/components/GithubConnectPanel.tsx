import { useState, useEffect } from "react";
import { Github, Link as LinkIcon, CheckCircle, AlertCircle } from "lucide-react";

const MOCK_CLIENT_ID = "123e4567-e89b-12d3-a456-426614174000";
const API_BASE = "http://localhost:8000";

interface Repository {
    name: string;
    default_branch: string;
}

export default function GithubConnectPanel() {
    const [isConnected, setIsConnected] = useState(false);
    const [repos, setRepos] = useState<Repository[]>([]);
    const [selectedRepo, setSelectedRepo] = useState<string>("");
    const [selectedBranch, setSelectedBranch] = useState<string>("");
    const [statusMessage, setStatusMessage] = useState<{ type: "success" | "error", text: string } | null>(null);
    const [isConnecting, setIsConnecting] = useState(false);

    useEffect(() => {
        const params = new URLSearchParams(window.location.search);
        if (params.get("github_connected") === "true") {
            setIsConnected(true);
            fetchRepositories();
            window.history.replaceState({}, document.title, window.location.pathname);
        }
    }, []);

    const handleLoginClick = () => {
        window.location.href = `${API_BASE}/github/login?client_id=${MOCK_CLIENT_ID}`;
    };

    const fetchRepositories = async () => {
        try {
            const res = await fetch(`${API_BASE}/github/repos?client_id=${MOCK_CLIENT_ID}`);
            if (!res.ok) throw new Error("Failed to fetch repositories");
            const data = await res.json();
            setRepos(data);
        } catch (err) {
            console.error(err);
            setStatusMessage({ type: "error", text: "Failed to load repositories." });
        }
    };

    const handleRepoChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
        const repoName = e.target.value;
        setSelectedRepo(repoName);
        const repo = repos.find(r => r.name === repoName);
        if (repo) {
            setSelectedBranch(repo.default_branch);
        }
    };

    const handleConnectRepo = async () => {
        if (!selectedRepo || !selectedBranch) return;
        setIsConnecting(true);
        setStatusMessage(null);
        try {
            const res = await fetch(`${API_BASE}/github/connect`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    client_id: MOCK_CLIENT_ID,
                    repo_url: `https://github.com/${selectedRepo}`,
                    default_branch: selectedBranch
                })
            });

            if (!res.ok) {
                const data = await res.json();
                throw new Error(data.detail || "Failed to connect repository");
            }

            setStatusMessage({ type: "success", text: "Repository connected and webhook registered!" });
        } catch (err: any) {
            setStatusMessage({ type: "error", text: err.message });
        } finally {
            setIsConnecting(false);
        }
    };

    return (
        <div className="w-64 bg-gray-900 border-r border-gray-700 flex flex-col h-full border-l">
            <div className="p-4 border-b border-gray-700">
                <h2 className="text-lg font-semibold text-white mb-2 flex items-center gap-2">
                    <Github className="w-5 h-5" />
                    Ingestion
                </h2>
                <p className="text-xs text-gray-400">
                    Sync your architecture automatically with GitHub.
                </p>
            </div>

            <div className="p-4 flex-1 overflow-y-auto">
                {!isConnected ? (
                    <div className="text-center mt-4">
                        <button
                            onClick={handleLoginClick}
                            className="w-full flex items-center justify-center gap-2 bg-gray-800 hover:bg-gray-700 text-white py-2 px-4 rounded-md border border-gray-600 transition-colors text-sm"
                        >
                            <Github className="w-4 h-4" />
                            Connect GitHub
                        </button>
                    </div>
                ) : (
                    <div className="space-y-4">
                        <div>
                            <label className="block text-xs font-medium text-gray-400 mb-1">
                                Repository
                            </label>
                            <select
                                value={selectedRepo}
                                onChange={handleRepoChange}
                                className="w-full bg-gray-800 border border-gray-600 rounded-md text-sm text-white p-2 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                            >
                                <option value="">Select a repository...</option>
                                {repos.map(r => (
                                    <option key={r.name} value={r.name}>{r.name}</option>
                                ))}
                            </select>
                        </div>

                        {selectedRepo && (
                            <div>
                                <label className="block text-xs font-medium text-gray-400 mb-1">
                                    Branch
                                </label>
                                <input
                                    type="text"
                                    value={selectedBranch}
                                    onChange={(e) => setSelectedBranch(e.target.value)}
                                    placeholder="e.g. main"
                                    className="w-full bg-gray-800 border border-gray-600 rounded-md text-sm text-white p-2 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                                />
                            </div>
                        )}

                        <button
                            onClick={handleConnectRepo}
                            disabled={!selectedRepo || !selectedBranch || isConnecting}
                            className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:text-gray-500 text-white py-2 px-4 rounded-md transition-colors text-sm mt-4"
                        >
                            <LinkIcon className="w-4 h-4" />
                            {isConnecting ? "Connecting..." : "Connect Repository"}
                        </button>

                        {statusMessage && (
                            <div className={`mt-4 p-3 rounded-md text-sm flex items-start gap-2 ${statusMessage.type === 'success' ? 'bg-green-900/30 text-green-400 border border-green-800/50' : 'bg-red-900/30 text-red-400 border border-red-800/50'}`}>
                                {statusMessage.type === 'success' ? <CheckCircle className="w-4 h-4 mt-0.5 shrink-0" /> : <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />}
                                <p>{statusMessage.text}</p>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
