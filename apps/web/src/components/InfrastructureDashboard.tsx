/**
 * This component is the infrastructure dashboard for the infrastructure design
 * and will be the main component for the infrastructure design.
 * It displays the list of designs and allows the user to create a new design.
 * It also allows the user to open a design and delete a design.
 */

import { Plus, Network, Calendar, Trash2, Copy, Check } from "lucide-react";
import type { InfrastructureDashboardProps } from "../types/infrastructure";
import { useState } from "react";

export default function InfrastructureDashboard({
  designs,
  loading = false,
  error = null,
  createPending = false,
  onCreateNew,
  onOpenDesign,
  onDeleteDesign,
}: InfrastructureDashboardProps) {
  const formatDate = (iso: string) => {
    const d = new Date(iso);
    const now = new Date();
    const diff = now.getTime() - d.getTime();
    if (diff < 86400000) return "Today";
    if (diff < 172800000) return "Yesterday";
    return d.toLocaleDateString();
  };

  const [copiedId, setCopiedId] = useState<string | null>(null);

  const handleCopyId = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    navigator.clipboard.writeText(id);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="min-h-screen bg-gray-950 p-8">
      <div className="max-w-6xl mx-auto">
        <header className="mb-10 flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">
              Infrastructure Designs
            </h1>
            <p className="text-gray-400 mt-1">
              View and manage your infrastructure diagrams
            </p>
          </div>
        </header>

        {error && (
          <div className="mb-6 p-4 rounded-lg bg-red-900/30 border border-red-700 text-red-300 text-sm">
            {error}
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-20 text-gray-400">
            Loading...
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              <button
                onClick={onCreateNew}
                disabled={createPending}
                className="aspect-square flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed border-gray-600 bg-gray-900/50 hover:border-blue-500 hover:bg-gray-800/80 transition-all group disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <div className="w-16 h-16 rounded-full bg-gray-800 flex items-center justify-center group-hover:bg-blue-500/20 transition-colors">
                  <Plus className="w-8 h-8 text-gray-400 group-hover:text-blue-400" />
                </div>
                <span className="text-sm font-medium text-gray-400 group-hover:text-gray-300">
                  {createPending ? "Creating..." : "Create new design"}
                </span>
              </button>

              {designs.map((design) => (
                <div
                  key={design.id}
                  className="aspect-square flex flex-col rounded-xl border border-gray-700 bg-gray-900 hover:border-gray-600 transition-all overflow-hidden group cursor-pointer"
                >
                  <div
                    onClick={() => onOpenDesign(design.id)}
                    className="flex-1 flex flex-col p-4"
                  >
                    <div className="flex items-start justify-between">
                      <div className="w-12 h-12 rounded-lg bg-gray-800 flex items-center justify-center">
                        <Network className="w-6 h-6 text-blue-400" />
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onDeleteDesign(design.id);
                        }}
                        className="p-1.5 rounded-md opacity-0 group-hover:opacity-100 hover:bg-red-500/20 text-gray-400 hover:text-red-400 transition-all"
                        title="Delete design"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                    <h3 className="mt-4 font-medium text-white truncate">
                      {design.name}
                    </h3>
                    <div
                      className="mt-1 flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-300 transition-colors cursor-copy"
                      onClick={(e) => handleCopyId(e, design.id)}
                      title="Copy Graph ID"
                    >
                      {copiedId === design.id ? (
                        <Check className="w-3 h-3 text-green-400" />
                      ) : (
                        <Copy className="w-3 h-3" />
                      )}
                      <span className="font-mono text-[10px] truncate max-w-[120px]">
                        {design.id}
                      </span>
                    </div>
                    <div className="mt-auto pt-4 flex items-center gap-2 text-xs text-gray-500">
                      <Calendar className="w-3.5 h-3.5" />
                      {formatDate(design.updatedAt)}
                    </div>
                    <p className="text-xs text-gray-500 mt-1">
                      {design.nodes.length} nodes · {design.edges.length}{" "}
                      connections
                    </p>
                  </div>
                </div>
              ))}
            </div>

            {designs.length === 0 && (
              <p className="text-center text-gray-500 mt-12">
                No designs yet. Click the card above to create your first
                infrastructure.
              </p>
            )}
          </>
        )}
      </div>
    </div>
  );
}
