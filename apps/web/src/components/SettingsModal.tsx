import { useState, useEffect } from "react";
import { Settings, Database, Github, CheckCircle, AlertCircle, Play } from "lucide-react";

const MOCK_CLIENT_ID = "123e4567-e89b-12d3-a456-426614174000";
const API_BASE = "http://localhost:8000";

interface SettingsModalProps {
    isOpen: boolean;
    onClose: () => void;
}

export default function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
    const [activeTab, setActiveTab] = useState<"aws" | "repos">("aws");

    // AWS State
    const [authMethod, setAuthMethod] = useState<"role" | "keys">("role");
    const [awsRegion, setAwsRegion] = useState("us-east-1");
    const [roleArn, setRoleArn] = useState("");
    const [externalId, setExternalId] = useState("");
    const [awsAccessKey, setAwsAccessKey] = useState("");
    const [awsSecretKey, setAwsSecretKey] = useState("");
    const [awsStatus, setAwsStatus] = useState<{ type: "success" | "error", text: string } | null>(null);
    const [isSaving, setIsSaving] = useState(false);

    // Repo State
    const [repos, setRepos] = useState<any[]>([]);
    const [loadingRepos, setLoadingRepos] = useState(false);
    const [ingesting, setIngesting] = useState<Record<string, boolean>>({});

    useEffect(() => {
        if (isOpen) {
            fetchIntegrations();
            fetchRepos();
        }
    }, [isOpen]);

    const fetchIntegrations = async () => {
        try {
            await fetch(`${API_BASE}/integrations/?client_id=${MOCK_CLIENT_ID}`);
            // We only see what's configured, we don't get the secret keys back
            // so we don't strictly prepopulate the form with secrets, just placeholders or visual indicators.
        } catch (e) {
            console.error("Failed to load integrations", e);
        }
    };

    const fetchRepos = async () => {
        setLoadingRepos(true);
        try {
            const res = await fetch(`${API_BASE}/github/connected-repos?client_id=${MOCK_CLIENT_ID}`);
            const data = await res.json();
            setRepos(data);
        } catch (e) {
            console.error("Failed to load repos", e);
        } finally {
            setLoadingRepos(false);
        }
    };

    const handleSaveAWS = async () => {
        setIsSaving(true);
        setAwsStatus(null);
        try {
            // Save AWS config
            const credentialsPayload: any = { region: awsRegion };
            if (authMethod === "role" && roleArn) {
                credentialsPayload.role_arn = roleArn;
                if (externalId) credentialsPayload.external_id = externalId;
            } else if (authMethod === "keys" && (awsAccessKey || awsSecretKey)) {
                credentialsPayload.aws_access_key_id = awsAccessKey;
                credentialsPayload.aws_secret_access_key = awsSecretKey;
            }

            if (Object.keys(credentialsPayload).length > 1) {
                await fetch(`${API_BASE}/integrations/aws?client_id=${MOCK_CLIENT_ID}`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ credentials: credentialsPayload })
                });
            }

            setAwsStatus({ type: "success", text: "Integrations saved successfully!" });
            setAwsAccessKey("");
            setAwsSecretKey("");
            setRoleArn("");
            setExternalId("");
        } catch (e: any) {
            setAwsStatus({ type: "error", text: e.message || "Failed to save integrations" });
        } finally {
            setIsSaving(false);
        }
    };

    const handleForceIngest = async (repo: any) => {
        setIngesting(prev => ({ ...prev, [repo.id]: true }));
        try {
            // Re-use the existing pipeline endpoint to trigger an ingest of github and AWS 
            // Better yet, we can hit the pipeline export directly
            await fetch(`${API_BASE}/pipeline/export`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    client_id: MOCK_CLIENT_ID,
                    include_aws: false,
                    include_github: true
                })
            });
            setTimeout(() => fetchRepos(), 2000); // refresh list
        } catch (e) {
            console.error("Failed to ingest", e);
        } finally {
            setIngesting(prev => ({ ...prev, [repo.id]: false }));
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4">
            <div className="bg-gray-900 border border-gray-700 rounded-xl w-full max-w-2xl overflow-hidden flex flex-col max-h-[90vh]">

                {/* Header */}
                <div className="px-6 py-4 border-b border-gray-800 flex justify-between items-center bg-gray-950">
                    <h2 className="text-xl font-semibold text-white flex items-center gap-2">
                        <Settings className="w-5 h-5" /> Provider Settings
                    </h2>
                    <button onClick={onClose} className="text-gray-400 hover:text-white transition-colors">
                        ✕
                    </button>
                </div>

                {/* Tabs */}
                <div className="flex border-b border-gray-800 bg-gray-900/50">
                    <button
                        className={`flex-1 py-3 px-4 text-sm font-medium transition-colors ${activeTab === 'aws' ? 'text-blue-400 border-b-2 border-blue-500 bg-gray-800/50' : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'}`}
                        onClick={() => setActiveTab("aws")}
                    >
                        <Database className="w-4 h-4 inline mr-2 mb-0.5" /> AWS Configuration
                    </button>
                    <button
                        className={`flex-1 py-3 px-4 text-sm font-medium transition-colors ${activeTab === 'repos' ? 'text-blue-400 border-b-2 border-blue-500 bg-gray-800/50' : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'}`}
                        onClick={() => setActiveTab("repos")}
                    >
                        <Github className="w-4 h-4 inline mr-2 mb-0.5" /> Repositories
                    </button>
                </div>

                {/* Content */}
                <div className="p-6 overflow-y-auto flex-1">
                    {activeTab === "aws" && (
                        <div className="space-y-6">
                            <div>
                                <h3 className="text-sm font-medium text-white mb-3 flex items-center justify-between">
                                    AWS Discovery Setup
                                </h3>

                                {/* Auth Method Toggle */}
                                <div className="flex bg-gray-800 p-1 rounded-lg mb-5 w-max">
                                    <button
                                        onClick={() => setAuthMethod("role")}
                                        className={`px-4 py-1.5 text-xs font-medium rounded-md transition-colors ${authMethod === 'role' ? 'bg-blue-600 text-white shadow' : 'text-gray-400 hover:text-white'}`}
                                    >
                                        Cross-Account Role (Recommended)
                                    </button>
                                    <button
                                        onClick={() => setAuthMethod("keys")}
                                        className={`px-4 py-1.5 text-xs font-medium rounded-md transition-colors ${authMethod === 'keys' ? 'bg-blue-600 text-white shadow' : 'text-gray-400 hover:text-white'}`}
                                    >
                                        Direct Access Keys
                                    </button>
                                </div>

                                {authMethod === "role" ? (
                                    <div className="grid grid-cols-2 gap-4 mb-4">
                                        <div>
                                            <label className="block text-xs text-gray-500 mb-1">IAM Role ARN *</label>
                                            <input type="text" value={roleArn} onChange={e => setRoleArn(e.target.value)} className="w-full bg-gray-800 border border-gray-700 rounded-lg p-2.5 text-sm text-white focus:border-blue-500 outline-none" placeholder="arn:aws:iam::123456789012:role/Opscribe" />
                                        </div>
                                        <div>
                                            <label className="block text-xs text-gray-500 mb-1">External ID (Optional)</label>
                                            <input type="text" value={externalId} onChange={e => setExternalId(e.target.value)} className="w-full bg-gray-800 border border-gray-700 rounded-lg p-2.5 text-sm text-white focus:border-blue-500 outline-none" placeholder="Secure token..." />
                                        </div>
                                    </div>
                                ) : (
                                    <div className="grid grid-cols-2 gap-4 mb-4">
                                        <div>
                                            <label className="block text-xs text-gray-500 mb-1">Access Key ID *</label>
                                            <input type="text" value={awsAccessKey} onChange={e => setAwsAccessKey(e.target.value)} className="w-full bg-gray-800 border border-gray-700 rounded-lg p-2.5 text-sm text-white focus:border-blue-500 outline-none" placeholder="AKIA..." />
                                        </div>
                                        <div>
                                            <label className="block text-xs text-gray-500 mb-1">Secret Access Key *</label>
                                            <input type="password" value={awsSecretKey} onChange={e => setAwsSecretKey(e.target.value)} className="w-full bg-gray-800 border border-gray-700 rounded-lg p-2.5 text-sm text-white focus:border-blue-500 outline-none" placeholder="••••••••••••••••" />
                                        </div>
                                    </div>
                                )}

                                <div>
                                    <label className="block text-xs text-gray-500 mb-1">Default AWS Region</label>
                                    <input type="text" value={awsRegion} onChange={e => setAwsRegion(e.target.value)} className="w-full bg-gray-800 border border-gray-700 rounded-lg p-2.5 text-sm text-white focus:border-blue-500 outline-none" placeholder="us-east-1" />
                                </div>
                            </div>

                            <hr className="border-gray-800" />

                            <div className="bg-blue-900/10 border border-blue-900/40 rounded-lg p-4">
                                <h4 className="text-sm font-semibold text-blue-400 mb-2">Required IAM Permissions</h4>
                                <p className="text-xs text-gray-400 mb-3 leading-relaxed">
                                    To allow Opscribe to discover your cloud architecture, you must attach the following JSON policy to your {authMethod === 'role' ? 'IAM Role' : 'IAM User'}.
                                    {authMethod === 'role' && " Ensure your role's Trust Relationship allows our AWS account to assume it."}
                                </p>
                                <pre className="bg-gray-950 p-3 rounded border border-gray-800 overflow-x-auto text-[10px] text-gray-300 font-mono leading-relaxed select-all">
                                    {`{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeInstances",
        "ec2:DescribeVpcs",
        "ec2:DescribeSubnets",
        "ec2:DescribeSecurityGroups",
        "rds:DescribeDBInstances",
        "lambda:ListFunctions",
        "s3:ListAllMyBuckets"
      ],
      "Resource": "*"
    }
  ]
}`}
                                </pre>
                            </div>

                            {awsStatus && (
                                <div className={`p-4 rounded-lg text-sm flex items-start gap-3 ${awsStatus.type === 'success' ? 'bg-green-900/20 text-green-400 border border-green-800/50' : 'bg-red-900/20 text-red-400 border border-red-800/50'}`}>
                                    {awsStatus.type === 'success' ? <CheckCircle className="w-5 h-5 shrink-0" /> : <AlertCircle className="w-5 h-5 shrink-0" />}
                                    <p className="mt-0.5">{awsStatus.text}</p>
                                </div>
                            )}

                            <div className="flex justify-end pt-4">
                                <button onClick={handleSaveAWS} disabled={isSaving} className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2.5 rounded-lg text-sm font-medium transition-colors disabled:opacity-50">
                                    {isSaving ? "Saving..." : "Save Configuration"}
                                </button>
                            </div>
                        </div>
                    )}

                    {activeTab === "repos" && (
                        <div>
                            <div className="flex justify-between items-center mb-6">
                                <div>
                                    <h3 className="text-sm font-medium text-white">Connected Repositories</h3>
                                    <p className="text-xs text-gray-400 mt-1">Repositories managed by your GitHub App Installation.</p>
                                </div>
                                <a href="http://localhost:8000/github/login?client_id=123e4567-e89b-12d3-a456-426614174000" className="bg-gray-800 hover:bg-gray-700 text-white px-4 py-2 rounded-lg text-xs font-medium border border-gray-700 flex items-center gap-2 transition-colors">
                                    <Github className="w-4 h-4" /> Install App
                                </a>
                            </div>

                            {loadingRepos ? (
                                <div className="text-center py-12 text-sm text-gray-500">Loading repositories...</div>
                            ) : repos.length === 0 ? (
                                <div className="text-center py-12 bg-gray-800/30 rounded-lg border border-gray-800 border-dashed">
                                    <Github className="w-8 h-8 text-gray-600 mx-auto mb-3" />
                                    <p className="text-sm text-gray-400 mb-1">No repositories connected.</p>
                                    <p className="text-xs text-gray-500">Install the Opscribe GitHub App on your organization to start discovering infrastructure.</p>
                                </div>
                            ) : (
                                <div className="space-y-3">
                                    {repos.map((repo: any) => (
                                        <div key={repo.id} className="bg-gray-800 rounded-lg border border-gray-700 p-4 flex items-center justify-between">
                                            <div>
                                                <div className="flex items-center gap-2 mb-1">
                                                    <span className="text-sm font-medium text-blue-400 bg-blue-400/10 px-2 py-0.5 rounded uppercase text-[10px] tracking-wide">
                                                        {repo.default_branch || "main"}
                                                    </span>
                                                    <a href={repo.repo_url} target="_blank" rel="noreferrer" className="text-sm font-medium text-gray-200 hover:text-white hover:underline truncate max-w-[200px]">
                                                        {repo.repo_url.replace("https://github.com/", "")}
                                                    </a>
                                                </div>
                                                <div className="text-xs text-gray-400 flex items-center gap-1.5 mt-2">
                                                    Status:
                                                    <span className={`capitalize font-medium ${repo.ingestion_status === 'success' ? 'text-green-400' : repo.ingestion_status === 'failed' ? 'text-red-400' : 'text-yellow-400'}`}>
                                                        {repo.ingestion_status || "Unknown"}
                                                    </span>
                                                    {repo.last_ingested_at && (
                                                        <span className="text-gray-600 ml-2">Last synced: {new Date(repo.last_ingested_at).toLocaleDateString()}</span>
                                                    )}
                                                </div>
                                            </div>

                                            {/* Ingest Now Indicator / Button */}
                                            {(!repo.last_ingested_at || repo.ingestion_status === 'failed') ? (
                                                <button
                                                    onClick={() => handleForceIngest(repo)}
                                                    disabled={ingesting[repo.id] || repo.ingestion_status === 'running'}
                                                    className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 text-white rounded-lg text-xs font-semibold whitespace-nowrap transition-colors animate-pulse hover:animate-none group shadow-[0_0_15px_rgba(37,99,235,0.3)]"
                                                >
                                                    <Play className="w-3.5 h-3.5 fill-current" />
                                                    {ingesting[repo.id] ? "Ingesting..." : "Ingest Now"}
                                                    <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-red-500 rounded-full animate-ping group-hover:hidden"></span>
                                                    <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-red-500 rounded-full group-hover:hidden"></span>
                                                </button>
                                            ) : (
                                                <button
                                                    onClick={() => handleForceIngest(repo)}
                                                    disabled={ingesting[repo.id] || repo.ingestion_status === 'running'}
                                                    className="flex items-center gap-2 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 text-gray-300 rounded text-xs transition-colors"
                                                >
                                                    Run Again
                                                </button>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}
                </div>

            </div>
        </div>
    );
}
