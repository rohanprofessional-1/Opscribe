import React, { useState } from "react";
import { Send, Loader2, Bot, User, Database } from "lucide-react";
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
}

/**
 * RAGChat Component
 * 
 * An embedded AI assistant that provides architectural insights based on the live graph.
 * It automatically syncs canvas changes and re-ingests data before each query to ensure
 * the LLM always has the most up-to-date context.
 */
export default function RAGChat({ clientId, graphId, nodes, edges, designName, onClose }: RAGChatProps) {
    const [query, setQuery] = useState("");
    const [loading, setLoading] = useState(false);
    const [messages, setMessages] = useState<Array<{ role: "user" | "bot"; content: string; metadata?: any; route?: string }>>([
        { role: "bot", content: "Hello! I am your AI architect. I am looking at the graph you are currently designing. Ask me anything about it!" }
    ]);
    const [status, setStatus] = useState<string | null>(null);

    const handleQuery = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!query.trim()) return;

        const userMsg = query;
        setMessages(prev => [...prev, { role: "user", content: userMsg }]);
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
            const res = await api.queryRag(clientId, userMsg, graphId);

            const botMsg = {
                role: "bot" as const,
                content: res.answer,
                metadata: res.items, // These are the chunks
                route: res.route,
            };

            setMessages(prev => [...prev, botMsg]);
        } catch (e: any) {
            setMessages(prev => [...prev, { role: "bot", content: `Error: ${e?.message || e}` }]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="w-80 flex flex-col h-full bg-gray-900 text-gray-100 border-l border-gray-700">
            <header className="flex items-center justify-between p-4 border-b border-gray-800 bg-gray-900/50">
                <div className="flex items-center gap-3">
                    <h2 className="text-lg font-semibold flex items-center gap-2">
                        <Bot className="text-blue-400 w-5 h-5" /> AI Assistant
                    </h2>
                </div>
                <button
                    onClick={onClose}
                    className="p-1 rounded hover:bg-gray-800 transition-colors"
                >
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-gray-400"><path d="M18 6 6 18" /><path d="m6 6 12 12" /></svg>
                </button>
            </header>


            {status && (
                <div className={`p-2 text-center text-xs ${status.startsWith("Error") ? "bg-red-900/30 text-red-300" : "bg-blue-900/30 text-blue-300"}`}>
                    {status}
                </div>
            )}

            <main className="flex-1 overflow-y-auto p-4 space-y-6 w-full">
                {messages.map((m, i) => (
                    <div key={i} className={`flex gap-4 ${m.role === "bot" ? "" : "flex-row-reverse"}`}>
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${m.role === "bot" ? "bg-blue-900/50 text-blue-400" : "bg-gray-800 text-gray-400"}`}>
                            {m.role === "bot" ? <Bot className="w-5 h-5" /> : <User className="w-5 h-5" />}
                        </div>
                        <div className={`max-w-[80%] p-4 rounded-2xl ${m.role === "bot" ? "bg-gray-900 border border-gray-800" : "bg-blue-600 text-white"}`}>
                            {m.role === "bot" && m.route && (
                                <span className={`inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider mb-2 px-2 py-0.5 rounded-full ${m.route === "traversal"
                                        ? "bg-purple-900/40 text-purple-300 border border-purple-700/50"
                                        : "bg-blue-900/40 text-blue-300 border border-blue-700/50"
                                    }`}>
                                    {m.route === "traversal" ? "🔀 Graph Traversal" : "📚 RAG"}
                                </span>
                            )}
                            <div className="whitespace-pre-wrap text-sm font-sans">{m.content}</div>
                            {m.metadata && (m.metadata as any[]).length > 0 && (
                                <div className="mt-4 pt-4 border-t border-gray-800">
                                    <span className="text-[10px] font-bold uppercase tracking-wider text-gray-500 flex items-center gap-1 mb-2">
                                        <Database className="w-3 h-3" /> Sources
                                    </span>
                                    <div className="grid gap-2">
                                        {(m.metadata as any[]).map((chunk, idx) => (
                                            <div key={idx} className="bg-gray-950 p-2 rounded-lg border border-gray-800 text-[11px] text-gray-400">
                                                <span className="text-blue-400 block mb-1">Source {idx + 1}</span>
                                                {chunk.content.substring(0, 200)}...
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
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
