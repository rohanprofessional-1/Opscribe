import { useState } from "react";
import { Plus, Network, Calendar, Trash2, Database } from "lucide-react";
import type { InfrastructureDashboardProps } from "../types/infrastructure";
import IngestionWizard from "./IngestionWizard";


export default function InfrastructureDashboard({
  designs,
  loading = false,
  error = null,
  onOpenDesign,
  onDeleteDesign,
  onIngestionTriggered,
  clientId,
}: InfrastructureDashboardProps) {
  const [isWizardOpen, setIsWizardOpen] = useState(false);


  const formatDate = (iso: string) => {
    const d = new Date(iso);
    const now = new Date();
    const diff = now.getTime() - d.getTime();
    if (diff < 86400000) return "Today";
    if (diff < 172800000) return "Yesterday";
    return d.toLocaleDateString();
  };

  const handleCreateNew = () => {
    setIsWizardOpen(true);
  };

  const handleIngestionStarted = (graphName: string) => {
    setIsWizardOpen(false);
    onIngestionTriggered(graphName);
  };

  // Standard Dashboard View
  return (
    <div className="min-h-screen bg-transparent relative p-8 md:p-12">
      <div className="max-w-7xl mx-auto">
        <header className="mb-12">
          <h1 className="text-4xl font-black text-white tracking-tight uppercase mb-2">
            Infrastructure Designs
          </h1>
          <p className="text-slate-500 font-medium text-lg">
            View and manage your architectural knowledge maps.
          </p>
        </header>

        {error && (
          <div className="mb-8 p-4 rounded-xl bg-red-950/20 border border-red-500/20 text-red-400 text-sm flex items-center gap-3">
            <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
            {error}
          </div>
        )}

        {loading ? (
          <div className="flex flex-col items-center justify-center py-32 text-gray-500 gap-4">
            <div className="w-8 h-8 border-2 border-white/5 border-t-blue-500 rounded-full animate-spin" />
            <span>Loading your designs...</span>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              <button
                onClick={handleCreateNew}
                className="aspect-square flex flex-col items-center justify-center gap-4 rounded-2xl border-2 border-dashed border-white/5 bg-white/[0.02] hover:border-blue-500/50 hover:bg-white/[0.05] transition-all group relative overflow-hidden"
              >
                <div className="w-16 h-16 rounded-2xl bg-white/5 flex items-center justify-center group-hover:bg-blue-500/20 group-hover:scale-110 transition-all duration-500">
                  <Plus className="w-8 h-8 text-gray-500 group-hover:text-blue-400" />
                </div>
                <div className="text-center">
                    <span className="block text-sm font-bold text-gray-400 group-hover:text-white transition-colors">
                      New Design
                    </span>
                    <span className="text-[10px] text-gray-600 uppercase tracking-widest font-bold mt-1 block">
                        Start Discovery
                    </span>
                </div>
                <div className="absolute inset-0 bg-gradient-to-br from-blue-500/0 to-blue-500/0 group-hover:from-blue-500/5 group-hover:to-transparent pointer-events-none" />
              </button>

              {designs.map((design) => (
                <div
                  key={design.id}
                  className="aspect-square flex flex-col rounded-2xl border border-white/5 bg-white/[0.02] hover:border-white/10 hover:bg-white/[0.04] transition-all overflow-hidden group cursor-pointer relative"
                >
                  <div
                    onClick={() => onOpenDesign(design.id)}
                    className="flex-1 flex flex-col p-6 z-10"
                  >
                    <div className="flex items-start justify-between">
                      <div className="w-12 h-12 rounded-xl bg-blue-500/10 flex items-center justify-center border border-blue-500/20 group-hover:scale-110 transition-transform duration-500 shadow-lg shadow-blue-500/5">
                        <Network className="w-6 h-6 text-blue-400" />
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onDeleteDesign(design.id);
                        }}
                        className="p-2 rounded-lg opacity-0 group-hover:opacity-100 hover:bg-red-500/10 text-gray-500 hover:text-red-400 transition-all"
                        title="Delete design"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                    
                    <div className="mt-6">
                        <h3 className="font-bold text-white text-lg truncate group-hover:text-blue-400 transition-colors">
                          {design.name}
                        </h3>
                        <div className="flex items-center gap-2 text-[10px] text-gray-500 mt-2 font-bold uppercase tracking-wider">
                          <Calendar className="w-3 h-3" />
                          {formatDate(design.updatedAt)}
                        </div>
                    </div>

                    <div className="mt-auto pt-4 flex items-center gap-4">
                        <div className="flex flex-col">
                            <span className="text-white font-bold text-sm">{design.nodes.length}</span>
                            <span className="text-[10px] text-gray-600 uppercase font-black">Nodes</span>
                        </div>
                        <div className="w-px h-6 bg-white/5" />
                        <div className="flex flex-col">
                            <span className="text-white font-bold text-sm tracking-tight">{design.edges.length}</span>
                            <span className="text-[10px] text-gray-600 uppercase font-black tracking-tighter">Edges</span>
                        </div>
                    </div>
                  </div>
                  <div className="absolute bottom-0 right-0 p-6 opacity-0 group-hover:opacity-10 scale-150 group-hover:scale-100 transition-all duration-700 pointer-events-none">
                     <Network className="w-24 h-24 text-blue-500" />
                  </div>
                </div>
              ))}
            </div>

            {designs.length === 0 && (
              <div className="text-center py-32 border-2 border-dashed border-white/5 rounded-3xl mt-12 bg-white/[0.01]">
                <div className="w-20 h-20 bg-white/5 rounded-full flex items-center justify-center mx-auto mb-6">
                    <Database className="w-10 h-10 text-gray-600" />
                </div>
                <h2 className="text-xl font-bold text-white mb-2">No infrastructure maps found</h2>
                <p className="text-gray-500 max-w-sm mx-auto">
                  Start discovery or create your first design manually to see it here.
                </p>
              </div>
            )}
          </>
        )}
      </div>

      <IngestionWizard 
        isOpen={isWizardOpen}
        onClose={() => setIsWizardOpen(false)}
        clientId={clientId}
        onIngestionStarted={handleIngestionStarted}
      />
    </div>
  );
}
