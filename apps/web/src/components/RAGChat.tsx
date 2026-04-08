import React, { useState } from "react";
import { Send, Loader2, Bot, User, History, X, PlusCircle, MessageSquare } from "lucide-react";
import { api } from "../api/client";
import type { Node, Edge } from "reactflow";
import type { InfrastructureNodeData } from "../types/infrastructure";

interface RAGChatProps {
    clientId: string;
    graphId: string;
    nodes: Node<InfrastructureNodeData>[];
    edges: Edge[];
    designName: string;
    onClose: () => void;
    persona: "pm" | "engineer";
    onPersonaChange: (persona: "pm" | "engineer") => void;
}

interface ChatSession {
    id: string;
    title: string;
    messages: ChatMessage[];
    persona: "pm" | "engineer";
    timestamp: number;
}

interface ChatMessage {
    role: "user" | "bot";
    content: string;
    metadata?: any;
    route?: string;
}

/**
 * RAGChat Component
 * 
 * An embedded AI assistant that provides architectural insights based on the live graph.
 * It automatically syncs canvas changes and re-ingests data before each query to ensure
 * the LLM always has the most up-to-date context.
 */
export default function RAGChat({ clientId, graphId, nodes, edges, designName, onClose, persona, onPersonaChange }: RAGChatProps) {
    const [query, setQuery] = useState("");
    const [loading, setLoading] = useState(false);
    const [status, setStatus] = useState<string | null>(null);
    const [isHistoryOpen, setIsHistoryOpen] = useState(false);
    
    // Sessions state
    const [sessions, setSessions] = useState<ChatSession[]>(() => {
        const saved = localStorage.getItem(`ops_chat_sessions_${graphId}`);
        return saved ? JSON.parse(saved) : [];
    });
    
    const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);

    // Current messages derived from current session or empty
    const currentSession = sessions.find(s => s.id === currentSessionId);
    const messages = currentSession?.messages || [];

    // Save to localStorage whenever sessions change
    React.useEffect(() => {
        localStorage.setItem(`ops_chat_sessions_${graphId}`, JSON.stringify(sessions));
    }, [sessions, graphId]);

    // PERSONA/GRAPH SWITCHING
    // When the persona or graph changes, we always land on the "Home" starting page
    // (Empty State) to avoid confusing contexts. Past chats remain in the history panel.
    React.useEffect(() => {
        setCurrentSessionId(null); 
    }, [persona, graphId]);

    const startNewSession = () => {
        const newId = Math.random().toString(36).substring(7);
        setCurrentSessionId(newId);
        setIsHistoryOpen(false);
    };

    const handleQuery = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!query.trim()) return;

        const userMsg = query;
        const tempId = currentSessionId || Math.random().toString(36).substring(7);
        
        const newUserMsg: ChatMessage = { role: "user", content: userMsg };
        
        // Update or create session
        setSessions(prev => {
            const existing = prev.find(s => s.id === tempId);
            if (existing) {
                return prev.map(s => s.id === tempId ? {
                    ...s,
                    messages: [...s.messages, newUserMsg],
                    timestamp: Date.now()
                } : s);
            } else {
                return [{
                    id: tempId,
                    title: userMsg.substring(0, 30) + (userMsg.length > 30 ? "..." : ""),
                    messages: [newUserMsg],
                    persona,
                    timestamp: Date.now()
                }, ...prev];
            }
        });

        if (!currentSessionId) setCurrentSessionId(tempId);
        
        setQuery("");
        setLoading(true);

        /**
         * AUTO-INGESTION WORKFLOW
         * 
         * To avoid manual ingestion steps, we execute a 'Sync -> Ingest -> Query' pipeline
         * on every user submission. This ensures semantic consistency between the 
         * visible canvas and the AI's knowledge base.
         */
        setStatus("Syncing graph changes...");

        try {
            // STEP 1: Persist the immediate ReactFlow canvas state to the PostgreSQL database.
            // This ensures the backend ingestor sees exactly what the user sees.
            await api.syncGraph(graphId, {
                name: designName,
                nodes: nodes.map(n => ({
                    id: n.id,
                    type: n.type ?? "infrastructureNode",
                    position: n.position,
                    data: (n.data ?? {}) as unknown as Record<string, unknown>,
                })),
                edges: edges.map(e => ({
                    id: e.id,
                    source: e.source,
                    target: e.target,
                    sourceHandle: e.sourceHandle ?? undefined,
                    targetHandle: e.targetHandle ?? undefined,
                })),
            });

            // STEP 2: Trigger the RAG engine to re-extract and vectorize the updated DB records.
            setStatus("Ingesting architecture vectors...");
            await api.ingestGraph(graphId);

            // STEP 3: Perform the vector retrieval and LLM inference.
            setStatus(null);
            const res = await api.queryRag(clientId, userMsg, graphId, 5, persona);

            const botMsg: ChatMessage = {
                role: "bot" as const,
                content: res.answer,
                metadata: res.items,
                route: res.route,
            };

            setSessions(prev => prev.map(s => s.id === tempId ? {
                ...s,
                messages: [...s.messages, botMsg]
            } : s));
        } catch (e: any) {
            const errorMsg: ChatMessage = { role: "bot", content: `Error: ${e?.message || e}` };
            setSessions(prev => prev.map(s => s.id === tempId ? {
                ...s,
                messages: [...s.messages, errorMsg]
            } : s));
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="w-96 flex flex-col h-full bg-gray-900 text-gray-100 border-l border-gray-700 relative overflow-hidden">
            {/* Click-away Overlay */}
            {isHistoryOpen && (
                <div 
                    className="absolute inset-0 bg-black/40 backdrop-blur-[2px] z-40 transition-opacity duration-300"
                    onClick={() => setIsHistoryOpen(false)}
                />
            )}

            {/* History Slideout */}
            <div className={`absolute inset-y-0 left-0 w-80 bg-gray-950 border-r border-gray-800 z-50 transition-transform duration-300 transform shadow-2xl ${isHistoryOpen ? "translate-x-0" : "-translate-x-full"}`}>
                <header className="p-4 border-b border-gray-800 flex items-center justify-between bg-gray-900">
                    <h3 className="text-xs font-black uppercase tracking-widest text-gray-500">History</h3>
                    <button 
                        onClick={() => setIsHistoryOpen(false)} 
                        className="p-1.5 hover:bg-red-500/20 hover:text-red-400 rounded-lg transition-all border border-transparent hover:border-red-500/30 text-gray-500"
                    >
                        <X className="w-4 h-4" />
                    </button>
                </header>
                <div className="p-2 space-y-1 overflow-y-auto h-[calc(100%-60px)]">
                    <button 
                        onClick={startNewSession}
                        className="w-full flex items-center gap-2 p-3 text-sm text-blue-400 hover:bg-blue-900/10 rounded-lg transition-colors mb-4 border border-blue-900/30"
                    >
                        <PlusCircle className="w-4 h-4" /> New Conversation
                    </button>
                    {sessions.map(s => (
                        <button
                            key={s.id}
                            onClick={() => {
                                setCurrentSessionId(s.id);
                                setIsHistoryOpen(false);
                                // Sync the dashboard persona with the resumed session's persona
                                onPersonaChange(s.persona);
                            }}
                            className={`w-full text-left p-3 rounded-lg text-sm transition-all group relative overflow-hidden ${currentSessionId === s.id ? "bg-blue-600/10 border border-blue-500/50 text-blue-100 shadow-[0_0_15px_rgba(59,130,246,0.1)]" : "hover:bg-gray-800 text-gray-400"}`}
                        >
                            {currentSessionId === s.id && (
                                <div className="absolute inset-y-0 left-0 w-1 bg-blue-500 shadow-[2px_0_10px_rgba(59,130,246,0.5)]" />
                            )}
                            <div className="flex items-center gap-2">
                                <MessageSquare className={`w-4 h-4 ${currentSessionId === s.id ? "text-blue-400" : "text-gray-600"}`} />
                                <span className="truncate flex-1 font-medium">{s.title}</span>
                            </div>
                            <div className="flex items-center gap-2 mt-1.5 px-6">
                                <span className={`text-[9px] px-1.5 py-0.5 rounded font-black tracking-widest uppercase ${s.persona === 'pm' ? 'bg-purple-900/40 text-purple-400 border border-purple-800/30' : 'bg-gray-800 text-gray-400 border border-gray-700/50'}`}>
                                    {s.persona === 'pm' ? 'PRD MANAGER' : 'ENGINEER'}
                                </span>
                                <span className="text-[9px] text-gray-600 font-medium">{new Date(s.timestamp).toLocaleDateString()}</span>
                            </div>
                        </button>
                    ))}
                </div>
            </div>

            {/* History Toggle Button */}
            <button 
                onClick={() => setIsHistoryOpen(true)}
                className={`absolute left-0 top-1/2 -translate-y-1/2 z-40 bg-gray-800 border border-gray-700 p-1.5 rounded-r-lg shadow-xl hover:bg-gray-700 transition-all ${isHistoryOpen ? "opacity-0 pointer-events-none" : "opacity-100"}`}
                title="History"
            >
                <History className="w-4 h-4 text-blue-400" />
            </button>

            <header className="flex items-center justify-between p-4 border-b border-gray-800 bg-gray-900/50">
                <div className="flex items-center gap-3">
                    <h2 className="text-lg font-semibold flex items-center gap-2">
                        <Bot className="text-blue-400 w-5 h-5" /> {currentSession ? currentSession.title : "AI Assistant"}
                    </h2>
                </div>
                <button
                    onClick={onClose}
                    className="p-1 rounded hover:bg-gray-800 transition-colors"
                >
                    <X className="w-5 h-5 text-gray-400" />
                </button>
            </header>

            {status && (
                <div className={`p-2 text-center text-xs ${status.startsWith("Error") ? "bg-red-900/30 text-red-300" : "bg-blue-900/30 text-blue-300"}`}>
                    {status}
                </div>
            )}

            <main className="flex-1 overflow-y-auto p-4 space-y-6 w-full scroll-smooth">
                {messages.length === 0 && (
                    <div className="h-full flex flex-col items-center justify-center text-center p-8">
                        <div className="relative mb-8">
                            <div className="absolute inset-0 bg-blue-500/20 blur-3xl rounded-full" />
                            <Bot className="w-16 h-16 relative text-blue-400 animate-pulse-slow" />
                        </div>
                        <h3 className="text-2xl font-bold mb-3 tracking-tight text-white">Opscribe Intelligence</h3>
                        <p className="text-sm text-gray-400 leading-relaxed max-w-[240px]">
                            I've analyzed your {designName} graph. Ask me about {persona === 'pm' ? 'business trade-offs or technical debt' : 'scaling, security, or implementation details'}.
                        </p>
                        <div className="mt-8 grid grid-cols-1 gap-2 w-full max-w-[200px]">
                            <button 
                                onClick={() => setQuery(persona === 'pm' ? 'What is the highest risk node?' : 'Explain the data flow.')}
                                className="text-[11px] font-bold uppercase tracking-widest p-2 rounded border border-gray-800 hover:border-blue-500/50 hover:bg-blue-500/5 transition-all text-gray-500 hover:text-blue-400"
                            >
                                {persona === 'pm' ? 'Identify Risks' : 'Analyze Flow'}
                            </button>
                        </div>
                    </div>
                )}
                {messages.map((m, i) => (
                    <div key={i} className={`flex gap-4 ${m.role === "bot" ? "" : "flex-row-reverse"}`}>
                        <div className={`w-9 h-9 rounded-full flex items-center justify-center shrink-0 shadow-lg ${m.role === "bot" ? "bg-blue-900/30 text-blue-400 border border-blue-500/20" : "bg-gray-800 text-gray-400 border border-gray-700"}`}>
                            {m.role === "bot" ? <Bot className="w-5 h-5" /> : <User className="w-5 h-5" />}
                        </div>
                        <div className={`max-w-[85%] p-4 rounded-2xl shadow-xl leading-relaxed ${m.role === "bot" ? "bg-gray-900/80 backdrop-blur-sm border border-gray-800 text-gray-200" : "bg-blue-600 text-white font-medium"}`}>
                            {m.role === "bot" && m.route && (
                                <span className={`inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider mb-2 px-2 py-0.5 rounded-full ${m.route === "traversal"
                                        ? "bg-purple-900/40 text-purple-300 border border-purple-700/50"
                                        : "bg-blue-900/40 text-blue-300 border border-blue-700/50"
                                    }`}>
                                    {m.route === "traversal" ? "🔀 Graph Traversal" : "📚 RAG"}
                                </span>
                            )}
                            <div className="whitespace-pre-wrap text-sm font-sans">{m.content}</div>
                        </div>
                    </div>
                ))}
                {loading && (
                    <div className="flex gap-4">
                        <div className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 bg-blue-900/50 text-blue-400">
                            <Bot className="w-5 h-5" />
                        </div>
                        <div className="p-4 rounded-2xl bg-gray-900 border border-gray-800">
                            <Loader2 className="w-5 h-5 animate-spin text-gray-500" />
                        </div>
                    </div>
                )}
            </main>

            <footer className="p-4 border-t border-gray-800 bg-gray-900/50">
                <form onSubmit={handleQuery} className="relative">
                    <input
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-3 pr-12 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                        placeholder="Ask the AI about your graph..."
                    />
                    <button
                        type="submit"
                        disabled={loading || !query.trim()}
                        className="absolute right-2 top-1/2 -translate-y-1/2 p-2 text-blue-400 hover:text-blue-300 disabled:opacity-50 transition-colors"
                    >
                        <Send className="w-5 h-5" />
                    </button>
                </form>
            </footer>
        </div>
    );
}
