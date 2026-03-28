/**
 * This component is the infrastructure dashboard for the infrastructure design
 * and will be the main component for the infrastructure design.
 * It displays the list of designs and allows the user to create a new design.
 * It also allows the user to open a design and delete a design.
 */

import { useState, useEffect } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import { Plus, Network, Calendar, Trash2, Settings as SettingsIcon, Database, Github, LogOut } from "lucide-react";
import type { InfrastructureDashboardProps } from "../types/infrastructure";
import SettingsModal from "./SettingsModal";
import { authFetch as fetch } from "../api/client";

const API_BASE = "http://localhost:8000";

export default function InfrastructureDashboard({
  designs,
  loading = false,
  error = null,
  createPending = false,
  onCreateNew,
  onOpenDesign,
  onDeleteDesign,
}: InfrastructureDashboardProps) {
  const { user, logout } = useAuth0();
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [settingsTab, setSettingsTab] = useState<"aws" | "repos" | undefined>(undefined);

  const [hasIntegrations, setHasIntegrations] = useState<boolean | null>(null);

  // Fetch integration status to determine if we should show the Onboarding Hero
  useEffect(() => {
    fetch(`${API_BASE}/clients/me`)
      .then(r => r.json())
      .then(d => {
        Promise.all([
          fetch(`${API_BASE}/integrations/?client_id=${d.id}`).then(r => r.json()),
          fetch(`${API_BASE}/github/connected-repos?client_id=${d.id}`).then(r => r.json())
        ]).then(([ints, repos]) => {
          const awsCount = Array.isArray(ints) ? ints.length : 0;
          const repoCount = Array.isArray(repos) ? repos.length : 0;
          setHasIntegrations(awsCount > 0 || repoCount > 0);
        }).catch(() => setHasIntegrations(true)); // Hide onboarding on error
      }).catch(() => setHasIntegrations(true));
  }, [isSettingsOpen]); // Re-check when Settings Modal closes

  const formatDate = (iso: string) => {
    const d = new Date(iso);
    const now = new Date();
    const diff = now.getTime() - d.getTime();
    if (diff < 86400000) return "Today";
    if (diff < 172800000) return "Yesterday";
    return d.toLocaleDateString();
  };

  const openSettings = (tab?: "aws" | "repos") => {
    setSettingsTab(tab);
    setIsSettingsOpen(true);
  };

  // The Onboarding Hero View for NET NEW clients
  if (designs.length === 0 && hasIntegrations === false && !loading) {
    return (
      <div className="min-h-screen bg-gray-950 p-8 flex items-center justify-center">
        <div className="max-w-3xl w-full text-center">
          <h1 className="text-4xl font-bold text-white mb-4">Welcome to Opscribe</h1>
          <p className="text-lg text-gray-400 mb-12">
            Let's build your infrastructure graph. Connect your cloud environment or codebase to get started.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <button
              onClick={() => openSettings("aws")}
              className="flex flex-col items-center justify-center p-10 bg-gray-900 border border-gray-800 hover:border-blue-500 rounded-2xl transition-all group"
            >
              <div className="w-16 h-16 bg-blue-500/10 rounded-full flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                <Database className="w-8 h-8 text-blue-400" />
              </div>
              <h3 className="text-xl font-semibold text-white mb-2">Connect AWS</h3>
              <p className="text-sm text-gray-500 text-center">
                Discover your VPCs, EC2s, RDS instances, and their relationships automatically using cross-account roles.
              </p>
            </button>

            <button
              onClick={() => openSettings("repos")}
              className="flex flex-col items-center justify-center p-10 bg-gray-900 border border-gray-800 hover:border-purple-500 rounded-2xl transition-all group"
            >
              <div className="w-16 h-16 bg-purple-500/10 rounded-full flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                <Github className="w-8 h-8 text-purple-400" />
              </div>
              <h3 className="text-xl font-semibold text-white mb-2">Connect GitHub</h3>
              <p className="text-sm text-gray-500 text-center">
                Install our application to parse Dockerfiles, Kubernetes manifests, and IaC to map your services.
              </p>
            </button>
          </div>
        </div>

        <SettingsModal
          isOpen={isSettingsOpen}
          initialTab={settingsTab}
          onClose={() => setIsSettingsOpen(false)}
        />
      </div>
    );
  }

  // Standard Dashboard View
  return (
    <div className="min-h-screen bg-[#020617] relative">
      <nav className="fixed top-0 left-0 w-full z-10 bg-[#01040a]/80 backdrop-blur-md border-b border-white/5 px-8 py-4 flex justify-between items-center shadow-lg">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg overflow-hidden flex items-center justify-center border border-white/10 bg-white/5">
            <img src="/logo.png" alt="Logo" className="w-full h-full object-contain" />
          </div>
          <span className="text-xl font-black tracking-tighter uppercase text-white">Opscribe</span>
        </div>

        <div className="flex items-center gap-4">
          <button
            onClick={() => openSettings()}
            className="flex items-center justify-center gap-2 p-2 px-3 border border-gray-700 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg transition-colors text-sm font-medium shadow-sm"
          >
            <SettingsIcon className="w-4 h-4" />
            Provider Settings
          </button>

          <div className="h-6 w-px bg-gray-800 mx-1"></div>

          <div className="flex items-center gap-3">
            {user?.picture ? (
              <img src={user.picture} alt={user?.name || "User"} className="w-8 h-8 rounded-full border border-gray-700 shadow-lg shadow-blue-500/20" />
            ) : (
              <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-[10px] font-bold text-white shadow-lg shadow-blue-500/20">
                {user?.name?.charAt(0)?.toUpperCase() || "U"}
              </div>
            )}
            <button
              onClick={() => logout({ logoutParams: { returnTo: window.location.origin } })}
              className="group flex items-center justify-center p-2 hover:bg-red-500/10 text-gray-400 hover:text-red-400 rounded-lg transition-colors"
              title="Log Out"
            >
              <LogOut className="w-4 h-4 group-hover:scale-110 transition-transform" />
            </button>
          </div>
        </div>
      </nav>

      <div className="max-w-6xl mx-auto pt-32 pb-20 px-4">
        <header className="mb-10 flex justify-between items-end">
          <div>
            <h1 className="text-3xl font-black text-white tracking-tight uppercase">
              Infrastructure Designs
            </h1>
            <p className="text-slate-500 mt-2 font-medium">
              View and manage your architectural knowledge maps.
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
                infrastructure. (Or wait for Auto-Discovery to finish!)
              </p>
            )}
          </>
        )}
      </div>

      <SettingsModal
        isOpen={isSettingsOpen}
        initialTab={settingsTab}
        onClose={() => setIsSettingsOpen(false)}
      />
    </div>
  );
}
