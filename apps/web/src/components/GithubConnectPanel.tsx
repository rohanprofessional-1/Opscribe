import { useState } from "react";
import { Github, Link as LinkIcon, CheckCircle, AlertCircle } from "lucide-react";
import { authFetch as fetch } from "../api/client";

// For the MVP, we assume a single mock client or one retrieved from context
const MOCK_CLIENT_ID = "123e4567-e89b-12d3-a456-426614174000";
const API_BASE = "http://localhost:8000";

export default function GithubConnectPanel() {
    const [repoUrl, setRepoUrl] = useState<string>("");
    const [branch, setBranch] = useState<string>("main");
    const [statusMessage, setStatusMessage] = useState<{ type: "success" | "error", text: string } | null>(null);
    const [isConnecting, setIsConnecting] = useState(false);

    const handleIngestRepo = async () => {
        if (!repoUrl) return;
        setIsConnecting(true);
        setStatusMessage(null);
        try {
            const res = await fetch(`${API_BASE}/pipeline/github-link`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    client_id: MOCK_CLIENT_ID,
                    repo_url: repoUrl,
                    branch: branch || "main"
                })
            });

            if (!res.ok) {
                const data = await res.json().catch(() => ({}));
                throw new Error(data.detail || "Failed to trigger ingestion");
            }

            setStatusMessage({ type: "success", text: "Ingestion started! Data will be exported to S3." });
            setRepoUrl("");
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
                    Paste a public GitHub URL to extract architecture and export to S3.
                </p>
            </div>

            <div className="p-4 flex-1 overflow-y-auto">
                <div className="space-y-4">
                    <div>
                        <label className="block text-xs font-medium text-gray-400 mb-1">
                            Repository URL
                        </label>
                        <input
                            type="text"
                            value={repoUrl}
                            onChange={(e) => setRepoUrl(e.target.value)}
                            placeholder="https://github.com/owner/repo"
                            className="w-full bg-gray-800 border border-gray-600 rounded-md text-sm text-white p-2 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                        />
                    </div>

                    <div>
                        <label className="block text-xs font-medium text-gray-400 mb-1">
                            Branch (Optional)
                        </label>
                        <input
                            type="text"
                            value={branch}
                            onChange={(e) => setBranch(e.target.value)}
                            placeholder="main"
                            className="w-full bg-gray-800 border border-gray-600 rounded-md text-sm text-white p-2 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                        />
                    </div>

                    <button
                        onClick={handleIngestRepo}
                        disabled={!repoUrl || isConnecting}
                        className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:text-gray-500 text-white py-2 px-4 rounded-md transition-colors text-sm mt-4"
                    >
                        <LinkIcon className="w-4 h-4" />
                        {isConnecting ? "Ingesting..." : "Ingest Repository"}
                    </button>

                    {statusMessage && (
                        <div className={`mt-4 p-3 rounded-md text-sm flex items-start gap-2 ${statusMessage.type === 'success' ? 'bg-green-900/30 text-green-400 border border-green-800/50' : 'bg-red-900/30 text-red-400 border border-red-800/50'}`}>
                            {statusMessage.type === 'success' ? <CheckCircle className="w-4 h-4 mt-0.5 shrink-0" /> : <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />}
                            <p>{statusMessage.text}</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
