import { useState, useEffect } from "react";
import { Settings, Database, Github, CheckCircle, AlertCircle, Play, Copy, Check, HardDrive, ChevronDown, ChevronRight, FileJson } from "lucide-react";
import { authFetch as fetch } from "../api/client";

const API_BASE = "http://localhost:8000";

interface SettingsModalProps {
    isOpen: boolean;
    onClose: () => void;
    initialTab?: "aws" | "repos";
}

export default function SettingsModal({ isOpen, onClose, initialTab }: SettingsModalProps) {
    const [activeTab, setActiveTab] = useState<"aws" | "repos">("aws");

    useEffect(() => {
        if (isOpen && initialTab) {
            setActiveTab(initialTab);
        }
    }, [isOpen, initialTab]);

    // Real client ID — fetched from /clients/me on mount
    const [clientId, setClientId] = useState<string | null>(null);
    useEffect(() => {
        fetch(`${API_BASE}/clients/me`)
            .then(r => r.json())
            .then(d => setClientId(d.id))
            .catch(() => console.error("Could not load client session from /clients/me"));
    }, []);

    // AWS State
    const [authMethod, setAuthMethod] = useState<"role" | "keys">("role");
    const [awsRegion, setAwsRegion] = useState("us-east-1");
    const [roleArn, setRoleArn] = useState("");
    const [externalId, setExternalId] = useState("");
    const [awsAccessKey, setAwsAccessKey] = useState("");
    const [awsSecretKey, setAwsSecretKey] = useState("");
    const [awsStatus, setAwsStatus] = useState<{ type: "success" | "error", text: string } | null>(null);
    const [isSaving, setIsSaving] = useState(false);

    // Github App install URL (fetched dynamically from backend)
    const [githubInstallUrl, setGithubInstallUrl] = useState<string | null>(null);

    // GitHub Config State
    const [ghAppSlug, setGhAppSlug] = useState("");
    const [ghAppId, setGhAppId] = useState("");
    const [ghPrivateKey, setGhPrivateKey] = useState("");
    const [ghWebhookSecret, setGhWebhookSecret] = useState("");
    const [isSavingGh, setIsSavingGh] = useState(false);
    const [ghStatus, setGhStatus] = useState<{ type: "success" | "error", text: string } | null>(null);
    const [copiedStates, setCopiedStates] = useState<Record<string, boolean>>({});

    // Data Lake State
    const [datalake, setDatalake] = useState<any>(null);
    const [datalakeLoading, setDatalakeLoading] = useState(false);
    const [datalakeExpanded, setDatalakeExpanded] = useState(false);
    const [jsonExpanded, setJsonExpanded] = useState(false);

    const handleCopy = (text: string, id: string) => {
        navigator.clipboard.writeText(text);
        setCopiedStates({ ...copiedStates, [id]: true });
        setTimeout(() => setCopiedStates(prev => ({ ...prev, [id]: false })), 2000);
    };

    useEffect(() => {
        if (clientId) {
            fetch(`${API_BASE}/github/config?client_id=${clientId}`)
                .then(r => r.json())
                .then(d => setGithubInstallUrl(d.app_install_url))
                .catch(() => setGithubInstallUrl(null));
        }
    }, [clientId]);

    // Repo State
    const [repos, setRepos] = useState<any[]>([]);
    const [loadingRepos, setLoadingRepos] = useState(false);
    const [ingesting, setIngesting] = useState<Record<string, boolean>>({});

    useEffect(() => {
        if (isOpen) {
            fetchIntegrations();
            fetchRepos();
            fetchDatalake();
        }
    }, [isOpen]);

    const fetchIntegrations = async () => {
        try {
            await fetch(`${API_BASE}/integrations/?client_id=${clientId}`);
        } catch (e) {
            console.error("Failed to load integrations", e);
        }
    };

    const fetchRepos = async () => {
        if (!clientId) return;
        setLoadingRepos(true);
        try {
            const res = await fetch(`${API_BASE}/github/repos?client_id=${clientId}`);
            if (res.ok) {
                const data = await res.json();
                setRepos(data);
            }
        } catch (error) {
            console.error("fetchRepos() EXCEPTION:", error);
        } finally {
            setLoadingRepos(false);
        }
    };

    const fetchDatalake = async () => {
        if (!clientId) return;
        setDatalakeLoading(true);
        try {
            const res = await fetch(`${API_BASE}/github/datalake?client_id=${clientId}`);
            if (res.ok) {
                const data = await res.json();
                setDatalake(data);
            }
        } catch (e) {
            console.error("Failed to load data lake preview", e);
        } finally {
            setDatalakeLoading(false);
        }
    };

    const handleSaveAWS = async () => {
        setIsSaving(true);
        setAwsStatus(null);
        try {
            const credentialsPayload: any = { region: awsRegion };
            if (authMethod === "role" && roleArn) {
                credentialsPayload.role_arn = roleArn;
                if (externalId) credentialsPayload.external_id = externalId;
            } else if (authMethod === "keys" && (awsAccessKey || awsSecretKey)) {
                credentialsPayload.aws_access_key_id = awsAccessKey;
                credentialsPayload.aws_secret_access_key = awsSecretKey;
            }

            if (Object.keys(credentialsPayload).length > 1) {
                const res = await fetch(`${API_BASE}/integrations/aws?client_id=${clientId}`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ credentials: credentialsPayload })
                });
                if (!res.ok) {
                    const errData = await res.json().catch(() => null);
                    throw new Error(errData?.detail || "Failed to validate and save AWS credentials.");
                }
                await fetch(`${API_BASE}/pipeline/export`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ client_id: clientId, include_aws: true, include_github: false, aws_region: awsRegion })
                });
            }
            setAwsStatus({ type: "success", text: "Integrations saved & discovery started!" });
            setAwsAccessKey(""); setAwsSecretKey(""); setRoleArn(""); setExternalId("");
        } catch (e: any) {
            setAwsStatus({ type: "error", text: e.message || "Failed to save integrations" });
        } finally {
            setIsSaving(false);
        }
    };

    const handleSaveGitHub = async () => {
        setIsSavingGh(true);
        setGhStatus(null);
        try {
            const res = await fetch(`${API_BASE}/integrations/github_app?client_id=${clientId}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ credentials: { github_app_slug: ghAppSlug, github_app_id: ghAppId, github_private_key: ghPrivateKey, github_webhook_secret: ghWebhookSecret } })
            });
            if (!res.ok) {
                const errorData = await res.json().catch(() => ({}));
                throw new Error(errorData.detail || "Failed to save configuration");
            }
            setGhStatus({ type: "success", text: "Successfully saved GitHub App credentials!" });
            await fetchRepos();
            fetch(`${API_BASE}/github/config?client_id=${clientId}`).then(r => r.json()).then(d => setGithubInstallUrl(d.app_install_url));
            setGhPrivateKey(""); setGhWebhookSecret("");
        } catch (e: any) {
            setGhStatus({ type: "error", text: e.message || "Failed to save integrations" });
        } finally {
            setIsSavingGh(false);
        }
    };

    const handleForceIngest = async (repo: any) => {
        setIngesting(prev => ({ ...prev, [repo.id]: true }));
        try {
            await fetch(`${API_BASE}/github/connect`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ client_id: clientId, repo_url: `https://github.com/${repo.name}`, target_repo_id: repo.id.toString(), default_branch: repo.default_branch || "main" })
            });
            setTimeout(() => { fetchRepos(); fetchDatalake(); }, 3000);
        } catch (e) {
            console.error("Failed to connect & ingest", e);
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
                    <button onClick={onClose} className="text-gray-400 hover:text-white transition-colors">✕</button>
                </div>

                {/* Tabs */}
                <div className="flex border-b border-gray-800 bg-gray-900/50">
                    <button className={`flex-1 py-3 px-4 text-sm font-medium transition-colors ${activeTab === 'aws' ? 'text-blue-400 border-b-2 border-blue-500 bg-gray-800/50' : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'}`} onClick={() => setActiveTab("aws")}>
                        <Database className="w-4 h-4 inline mr-2 mb-0.5" /> AWS Configuration
                    </button>
                    <button className={`flex-1 py-3 px-4 text-sm font-medium transition-colors ${activeTab === 'repos' ? 'text-blue-400 border-b-2 border-blue-500 bg-gray-800/50' : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'}`} onClick={() => setActiveTab("repos")}>
                        <Github className="w-4 h-4 inline mr-2 mb-0.5" /> Repositories
                    </button>
                </div>

                {/* Content */}
                <div className="p-6 overflow-y-auto flex-1">
                    {activeTab === "aws" && (
                        <div className="space-y-6">
                            <div>
                                <h3 className="text-sm font-medium text-white mb-3">AWS Discovery Setup</h3>
                                <div className="flex bg-gray-800 p-1 rounded-lg mb-5 w-max">
                                    <button onClick={() => setAuthMethod("role")} className={`px-4 py-1.5 text-xs font-medium rounded-md transition-colors ${authMethod === 'role' ? 'bg-blue-600 text-white shadow' : 'text-gray-400 hover:text-white'}`}>Cross-Account Role (Recommended)</button>
                                    <button onClick={() => setAuthMethod("keys")} className={`px-4 py-1.5 text-xs font-medium rounded-md transition-colors ${authMethod === 'keys' ? 'bg-blue-600 text-white shadow' : 'text-gray-400 hover:text-white'}`}>Direct Access Keys</button>
                                </div>
                                {authMethod === "role" ? (
                                    <div className="grid grid-cols-2 gap-4 mb-4">
                                        <div><label className="block text-xs text-gray-500 mb-1">IAM Role ARN *</label><input type="text" value={roleArn} onChange={e => setRoleArn(e.target.value)} className="w-full bg-gray-800 border border-gray-700 rounded-lg p-2.5 text-sm text-white focus:border-blue-500 outline-none" placeholder="arn:aws:iam::123456789012:role/Opscribe" /></div>
                                        <div><label className="block text-xs text-gray-500 mb-1">External ID (Optional)</label><input type="text" value={externalId} onChange={e => setExternalId(e.target.value)} className="w-full bg-gray-800 border border-gray-700 rounded-lg p-2.5 text-sm text-white focus:border-blue-500 outline-none" placeholder="Secure token..." /></div>
                                    </div>
                                ) : (
                                    <div className="grid grid-cols-2 gap-4 mb-4">
                                        <div><label className="block text-xs text-gray-500 mb-1">Access Key ID *</label><input type="text" value={awsAccessKey} onChange={e => setAwsAccessKey(e.target.value)} className="w-full bg-gray-800 border border-gray-700 rounded-lg p-2.5 text-sm text-white focus:border-blue-500 outline-none" placeholder="AKIA..." /></div>
                                        <div><label className="block text-xs text-gray-500 mb-1">Secret Access Key *</label><input type="password" value={awsSecretKey} onChange={e => setAwsSecretKey(e.target.value)} className="w-full bg-gray-800 border border-gray-700 rounded-lg p-2.5 text-sm text-white focus:border-blue-500 outline-none" placeholder="••••••••••••••••" /></div>
                                    </div>
                                )}
                                <div><label className="block text-xs text-gray-500 mb-1">Default AWS Region</label><input type="text" value={awsRegion} onChange={e => setAwsRegion(e.target.value)} className="w-full bg-gray-800 border border-gray-700 rounded-lg p-2.5 text-sm text-white focus:border-blue-500 outline-none" placeholder="us-east-1" /></div>
                            </div>
                            <hr className="border-gray-800" />
                            <div className="bg-blue-900/10 border border-blue-900/40 rounded-lg p-4">
                                <h4 className="text-sm font-semibold text-blue-400 mb-2">Required IAM Permissions</h4>
                                <p className="text-xs text-gray-400 mb-3 leading-relaxed">
                                    To allow Opscribe to discover your cloud architecture, attach this policy to your {authMethod === 'role' ? 'IAM Role' : 'IAM User'}.
                                    {authMethod === 'role' && " Ensure your role's Trust Relationship allows our AWS account to assume it."}
                                </p>
                                <pre className="bg-gray-950 p-3 rounded border border-gray-800 overflow-x-auto text-[10px] text-gray-300 font-mono leading-relaxed select-all">{`{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["ec2:DescribeInstances","ec2:DescribeVpcs","ec2:DescribeSubnets","ec2:DescribeSecurityGroups","rds:DescribeDBInstances","lambda:ListFunctions","s3:ListAllMyBuckets"],
    "Resource": "*"
  }]
}`}</pre>
                            </div>
                            {awsStatus && (
                                <div className={`p-4 rounded-lg text-sm flex items-start gap-3 ${awsStatus.type === 'success' ? 'bg-green-900/20 text-green-400 border border-green-800/50' : 'bg-red-900/20 text-red-400 border border-red-800/50'}`}>
                                    {awsStatus.type === 'success' ? <CheckCircle className="w-5 h-5 shrink-0" /> : <AlertCircle className="w-5 h-5 shrink-0" />}
                                    <p className="mt-0.5">{awsStatus.text}</p>
                                </div>
                            )}
                            <div className="flex justify-end pt-4">
                                <button onClick={handleSaveAWS} disabled={isSaving} className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2.5 rounded-lg text-sm font-medium transition-colors disabled:opacity-50">{isSaving ? "Saving..." : "Save Configuration and Ingest New Data"}</button>
                            </div>
                        </div>
                    )}

                    {activeTab === "repos" && (
                        <div>
                            {/* Step 1: Create GitHub App */}
                            <div className="mb-6 bg-gray-800/50 border border-gray-700 rounded-xl p-4">
                                <div className="flex items-start gap-3">
                                    <div className="w-6 h-6 rounded-full bg-blue-600 text-white flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">1</div>
                                    <div className="flex-1 w-full min-w-0">
                                        <h3 className="text-sm font-semibold text-white mb-2">Create or Configure a GitHub App</h3>
                                        <p className="text-xs text-gray-400 mb-4 leading-relaxed">
                                            Opscribe requires a dedicated GitHub App installed on your Organization. Go to <strong>Settings {">"} Developer Settings {">"} GitHub Apps</strong> and ensure the following values are set:
                                        </p>
                                        <div className="grid grid-cols-1 gap-2 text-xs mb-4">
                                            <div className="bg-gray-950 p-2.5 rounded border border-gray-800 flex justify-between items-center group w-full">
                                                <span className="text-gray-500 w-32 shrink-0">Homepage URL</span>
                                                <div className="flex items-center gap-2 overflow-hidden flex-1 justify-end">
                                                    <span className="text-gray-300 font-mono whitespace-nowrap overflow-x-auto no-scrollbar">{window.location.origin}</span>
                                                    <button onClick={() => handleCopy(window.location.origin, 'home')} className="text-gray-500 hover:text-white shrink-0 p-1">{copiedStates['home'] ? <Check className="w-3.5 h-3.5 text-green-400" /> : <Copy className="w-3.5 h-3.5" />}</button>
                                                </div>
                                            </div>
                                            <div className="bg-gray-950 p-2.5 rounded border border-gray-800 flex justify-between items-center group w-full">
                                                <span className="text-gray-500 w-32 shrink-0">Setup URL</span>
                                                <div className="flex items-center gap-2 overflow-hidden flex-1 justify-end">
                                                    <span className="text-gray-300 font-mono whitespace-nowrap overflow-x-auto no-scrollbar">{window.location.origin}/api/github/app/callback?client_id={clientId}</span>
                                                    <button onClick={() => handleCopy(`${window.location.origin}/api/github/app/callback?client_id=${clientId}`, 'callback')} className="text-gray-500 hover:text-white shrink-0 p-1">{copiedStates['callback'] ? <Check className="w-3.5 h-3.5 text-green-400" /> : <Copy className="w-3.5 h-3.5" />}</button>
                                                </div>
                                            </div>
                                            <div className="bg-gray-950 p-2.5 rounded border border-gray-800 flex justify-between items-center group w-full">
                                                <span className="text-gray-500 w-32 shrink-0">Webhook URL</span>
                                                <div className="flex items-center gap-2 overflow-hidden flex-1 justify-end">
                                                    <span className="text-gray-300 font-mono whitespace-nowrap overflow-x-auto no-scrollbar">{window.location.origin}/api/github/webhook?client_id={clientId}</span>
                                                    <button onClick={() => handleCopy(`${window.location.origin}/api/github/webhook?client_id=${clientId}`, 'webhook')} className="text-gray-500 hover:text-white shrink-0 p-1">{copiedStates['webhook'] ? <Check className="w-3.5 h-3.5 text-green-400" /> : <Copy className="w-3.5 h-3.5" />}</button>
                                                </div>
                                            </div>
                                        </div>
                                        <p className="text-xs text-blue-400 font-medium mb-1">Important Settings:</p>
                                        <ul className="text-xs text-gray-400 list-disc list-inside ml-1">
                                            <li>Under <b>Post Installation</b>, check <b>"Redirect on update"</b>.</li>
                                            <li>Repository Permissions: Contents (Read), Metadata (Read), Workflows (Read)</li>
                                        </ul>
                                    </div>
                                </div>
                            </div>

                            {/* Step 2: Configure Credentials */}
                            <div className="mb-6 bg-gray-800/50 border border-gray-700 rounded-xl p-4">
                                <div className="flex items-start gap-3">
                                    <div className="w-6 h-6 rounded-full bg-blue-600 text-white flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">2</div>
                                    <div className="flex-1">
                                        <h3 className="text-sm font-semibold text-white mb-4">Configure App Credentials</h3>
                                        <div className="grid grid-cols-2 gap-4 mb-4">
                                            <div><label className="block text-xs text-gray-500 mb-1">App Name (Slug) *</label><input type="text" value={ghAppSlug} onChange={e => setGhAppSlug(e.target.value)} className="w-full bg-gray-900 border border-gray-700 rounded-lg p-2.5 text-sm text-white focus:border-blue-500 outline-none" placeholder="my-company-opscribe" /></div>
                                            <div><label className="block text-xs text-gray-500 mb-1">App ID *</label><input type="text" value={ghAppId} onChange={e => setGhAppId(e.target.value)} className="w-full bg-gray-900 border border-gray-700 rounded-lg p-2.5 text-sm text-white focus:border-blue-500 outline-none" placeholder="123456" /></div>
                                        </div>
                                        <div className="mb-4"><label className="block text-xs text-gray-500 mb-1">Webhook Secret (Optional)</label><input type="password" value={ghWebhookSecret} onChange={e => setGhWebhookSecret(e.target.value)} className="w-full bg-gray-900 border border-gray-700 rounded-lg p-2.5 text-sm text-white focus:border-blue-500 outline-none" placeholder="Enter the secret you created..." /></div>
                                        <div className="mb-4"><label className="block text-xs text-gray-500 mb-1">Private Key (PEM) *</label><textarea value={ghPrivateKey} onChange={e => setGhPrivateKey(e.target.value)} rows={4} className="w-full bg-gray-900 border border-gray-700 rounded-lg p-2.5 text-xs font-mono text-gray-300 focus:border-blue-500 outline-none" placeholder={"-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----"} /></div>
                                        {ghStatus && (
                                            <div className={`p-4 mb-4 rounded-lg text-sm flex items-start gap-3 ${ghStatus.type === 'success' ? 'bg-green-900/20 text-green-400 border border-green-800/50' : 'bg-red-900/20 text-red-400 border border-red-800/50'}`}>
                                                {ghStatus.type === 'success' ? <CheckCircle className="w-5 h-5 shrink-0" /> : <AlertCircle className="w-5 h-5 shrink-0" />}
                                                <p className="mt-0.5">{ghStatus.text}</p>
                                            </div>
                                        )}
                                        <div className="flex justify-end"><button onClick={handleSaveGitHub} disabled={isSavingGh} className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50">{isSavingGh ? "Saving..." : "Save Credentials"}</button></div>
                                    </div>
                                </div>
                            </div>

                            {/* Step 3: Map Repos */}
                            <div className={`mb-6 p-4 rounded-xl border transition-colors ${githubInstallUrl ? 'bg-gray-800 border-gray-700' : 'bg-gray-900/50 border-gray-800/50 opacity-50'}`}>
                                <div className="flex items-start gap-3">
                                    <div className={`w-6 h-6 rounded-full text-white flex items-center justify-center text-xs font-bold shrink-0 mt-0.5 ${githubInstallUrl ? 'bg-blue-600' : 'bg-gray-700'}`}>3</div>
                                    <div className="flex-1">
                                        <div className="flex items-center justify-between mb-2">
                                            <h3 className="text-sm font-semibold text-white">Select Repositories</h3>
                                            {githubInstallUrl && (
                                                <a href={githubInstallUrl} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 bg-purple-600 hover:bg-purple-500 text-white px-3 py-1.5 rounded text-xs font-medium transition-colors shadow-sm">
                                                    <Github className="w-3.5 h-3.5" /> Install App to Repos
                                                </a>
                                            )}
                                        </div>
                                        <p className="text-xs text-gray-400 mb-4">Authorize Opscribe on specific repositories to map their infrastructure.</p>
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
                                                                <span className="text-sm font-medium text-blue-400 bg-blue-400/10 px-2 py-0.5 rounded uppercase text-[10px] tracking-wide">{repo.default_branch || "main"}</span>
                                                                <a href={`https://github.com/${repo.name}`} target="_blank" rel="noreferrer" className="text-sm font-medium text-gray-200 hover:text-white hover:underline truncate max-w-[250px]">{repo.name}</a>
                                                            </div>
                                                            <div className="text-xs text-green-400 flex items-center gap-1.5 mt-2 font-medium">✓ Connected</div>
                                                        </div>
                                                        {(!repo.last_ingested_at || repo.ingestion_status === 'failed') ? (
                                                            <button onClick={() => handleForceIngest(repo)} disabled={ingesting[repo.id] || repo.ingestion_status === 'running'} className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 text-white rounded-lg text-xs font-semibold whitespace-nowrap transition-colors animate-pulse hover:animate-none group shadow-[0_0_15px_rgba(37,99,235,0.3)]">
                                                                <Play className="w-3.5 h-3.5 fill-current" />
                                                                {ingesting[repo.id] ? "Connecting..." : "Connect & Ingest"}
                                                                <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-red-500 rounded-full animate-ping group-hover:hidden"></span>
                                                                <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-red-500 rounded-full group-hover:hidden"></span>
                                                            </button>
                                                        ) : (
                                                            <button onClick={() => handleForceIngest(repo)} disabled={ingesting[repo.id] || repo.ingestion_status === 'running'} className="flex items-center gap-2 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 text-gray-300 rounded text-xs transition-colors">Run Again</button>
                                                        )}
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>

                            {/* ── Step 4: Data Lake Preview ─────────────────────── */}
                            <div className="mb-6 p-4 rounded-xl border border-emerald-800/40 bg-emerald-950/20">
                                <div className="flex items-start gap-3">
                                    <div className="w-6 h-6 rounded-full bg-emerald-600 text-white flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">
                                        <HardDrive className="w-3.5 h-3.5" />
                                    </div>
                                    <div className="flex-1">
                                        <div className="flex items-center justify-between mb-2">
                                            <h3 className="text-sm font-semibold text-white">Data Lake Preview</h3>
                                            <button onClick={fetchDatalake} disabled={datalakeLoading} className="text-xs text-emerald-400 hover:text-emerald-300 transition-colors disabled:opacity-50">
                                                {datalakeLoading ? "Loading..." : "↻ Refresh"}
                                            </button>
                                        </div>
                                        <p className="text-xs text-gray-400 mb-4">Live view of your MinIO S3 data lake — every ingestion produces an immutable snapshot here.</p>

                                        {datalake ? (
                                            <div className="space-y-3">
                                                {/* Summary stats */}
                                                <div className="grid grid-cols-3 gap-2">
                                                    <div className="bg-gray-800/60 rounded-lg p-3 text-center border border-gray-700/50">
                                                        <div className="text-lg font-bold text-emerald-400">{datalake.file_count}</div>
                                                        <div className="text-[10px] text-gray-500 uppercase tracking-wider">Objects</div>
                                                    </div>
                                                    <div className="bg-gray-800/60 rounded-lg p-3 text-center border border-gray-700/50">
                                                        <div className="text-lg font-bold text-blue-400">{datalake.latest_payload?.summary?.total_nodes ?? "—"}</div>
                                                        <div className="text-[10px] text-gray-500 uppercase tracking-wider">Nodes</div>
                                                    </div>
                                                    <div className="bg-gray-800/60 rounded-lg p-3 text-center border border-gray-700/50">
                                                        <div className="text-lg font-bold text-purple-400">{datalake.latest_payload?.summary?.total_edges ?? "—"}</div>
                                                        <div className="text-[10px] text-gray-500 uppercase tracking-wider">Edges</div>
                                                    </div>
                                                </div>

                                                {/* File tree */}
                                                <button onClick={() => setDatalakeExpanded(!datalakeExpanded)} className="flex items-center gap-2 text-xs text-gray-300 hover:text-white transition-colors w-full">
                                                    {datalakeExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                                                    <HardDrive className="w-3.5 h-3.5 text-emerald-500" />
                                                    <span className="font-mono">s3://{datalake.bucket}/{datalake.client_id}/</span>
                                                </button>

                                                {datalakeExpanded && (
                                                    <div className="bg-gray-950 rounded-lg border border-gray-800 p-3 max-h-40 overflow-y-auto">
                                                        {datalake.files.map((f: any, i: number) => (
                                                            <div key={i} className="flex items-center gap-2 py-1 text-[11px] font-mono text-gray-400 hover:text-gray-200 transition-colors">
                                                                <FileJson className="w-3 h-3 text-emerald-600 shrink-0" />
                                                                <span className="truncate">{f.key.replace(`${datalake.client_id}/`, "")}</span>
                                                                <span className="text-gray-600 ml-auto shrink-0">{f.size_bytes > 1024 ? `${(f.size_bytes / 1024).toFixed(1)}KB` : `${f.size_bytes}B`}</span>
                                                            </div>
                                                        ))}
                                                    </div>
                                                )}

                                                {/* Latest payload preview */}
                                                {datalake.latest_payload && (
                                                    <>
                                                        <button onClick={() => setJsonExpanded(!jsonExpanded)} className="flex items-center gap-2 text-xs text-gray-300 hover:text-white transition-colors w-full">
                                                            {jsonExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                                                            <FileJson className="w-3.5 h-3.5 text-blue-500" />
                                                            <span>latest.json</span>
                                                            <span className="ml-auto text-[10px] text-gray-600">schema: {datalake.latest_payload.schema_version} · {datalake.latest_payload.ingestion_metadata?.commit_sha?.slice(0, 7)}</span>
                                                        </button>
                                                        {jsonExpanded && (
                                                            <pre className="bg-gray-950 rounded-lg border border-gray-800 p-3 max-h-60 overflow-auto text-[10px] font-mono text-gray-300 leading-relaxed">
                                                                {JSON.stringify(datalake.latest_payload, null, 2)}
                                                            </pre>
                                                        )}
                                                    </>
                                                )}
                                            </div>
                                        ) : datalakeLoading ? (
                                            <div className="text-center py-8 text-sm text-gray-500">Loading data lake…</div>
                                        ) : (
                                            <div className="text-center py-8 bg-gray-800/30 rounded-lg border border-gray-800 border-dashed">
                                                <HardDrive className="w-8 h-8 text-gray-600 mx-auto mb-3" />
                                                <p className="text-sm text-gray-400 mb-1">No data lake entries yet.</p>
                                                <p className="text-xs text-gray-500">Connect and ingest a repository to populate your S3 data lake.</p>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
