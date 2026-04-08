import { Layout, Network, Database, Github, Plus, Settings, LogOut, CheckCircle, AlertCircle, ChevronRight, ChevronLeft, Menu } from "lucide-react";
import type { InfrastructureDesign } from "../types/infrastructure";

interface SidebarProps {
  designs: InfrastructureDesign[];
  activeDesignId: string | null;
  onOpenDesign: (id: string) => void;
  onNewDesign: () => void;
  onOpenSettings: (tab?: "aws" | "repos") => void;
  awsConnected: boolean | null;
  githubConnected: boolean | null;
  user: any;
  onLogout: () => void;
  isCollapsed: boolean;
  setIsCollapsed: (collapsed: boolean) => void;
}

export default function Sidebar({
  designs,
  activeDesignId,
  onOpenDesign,
  onNewDesign,
  onOpenSettings,
  awsConnected,
  githubConnected,
  user,
  onLogout,
  isCollapsed,
  setIsCollapsed
}: SidebarProps) {
  return (
    <aside className={`h-screen bg-[#01040a] border-r border-white/5 flex flex-col z-20 shrink-0 sticky top-0 transition-all duration-300 ease-in-out ${isCollapsed ? 'w-20' : 'w-72'}`}>
      {/* Branding */}
      <div className={`p-6 border-b border-white/5 flex items-center justify-between transition-all ${isCollapsed ? 'px-4 justify-center' : 'px-6'}`}>
        {!isCollapsed && (
          <div className="flex items-center gap-3 overflow-hidden">
            <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center shadow-lg shadow-blue-500/20 group hover:scale-105 transition-transform duration-300 shrink-0">
               <img src="/logo.png" alt="Logo" className="w-6 h-6 object-contain" />
            </div>
            <span className="text-xl font-black tracking-tighter uppercase text-white animate-in fade-in duration-500">Opscribe</span>
          </div>
        )}
        <button 
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="p-1.5 hover:bg-white/5 rounded-lg text-gray-500 hover:text-white transition-all"
          title={isCollapsed ? "Expand Sidebar" : "Collapse Sidebar"}
        >
          {isCollapsed ? <Menu className="w-5 h-5" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>

      {/* Navigation / Graphs */}
      {!isCollapsed && (
        <div className="flex-1 overflow-y-auto py-6 px-4 space-y-8 custom-scrollbar animate-in fade-in duration-500">
          <div>
            <div className="flex items-center justify-between px-2 mb-4">
              <h3 className="text-[10px] font-bold text-gray-500 uppercase tracking-widest flex items-center gap-2">
                <Layout className="w-3 h-3" /> My Graphs
              </h3>
              <button 
                onClick={onNewDesign}
                className="p-1 hover:bg-white/5 rounded-md text-gray-400 hover:text-blue-400 transition-colors"
                title="Create new design"
              >
                <Plus className="w-4 h-4" />
              </button>
            </div>
            
            <div className="space-y-1">
              {designs.length === 0 ? (
                <p className="text-[11px] text-gray-600 px-2 italic">No graphs yet</p>
              ) : (
                designs.map((design) => (
                  <button
                    key={design.id}
                    onClick={() => {
                      onOpenDesign(design.id);
                      setIsCollapsed(true);
                    }}
                    className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all text-left group ${
                      activeDesignId === design.id 
                        ? 'bg-blue-600/10 text-blue-400 border border-blue-500/20 shadow-[0_0_15px_rgba(59,130,246,0.1)]' 
                        : 'text-gray-400 hover:bg-white/5 border border-transparent hover:text-gray-200'
                    }`}
                  >
                    <Network className={`w-4 h-4 shrink-0 ${activeDesignId === design.id ? 'text-blue-400' : 'text-gray-500 group-hover:text-blue-400'}`} />
                    <span className="text-sm font-medium truncate flex-1">{design.name}</span>
                    {activeDesignId === design.id && <ChevronRight className="w-3 h-3" />}
                  </button>
                ))
              )}
            </div>
          </div>

          {/* Connections Section */}
          <div>
             <h3 className="text-[10px] font-bold text-gray-500 uppercase tracking-widest flex items-center gap-2 px-2 mb-4">
              Connect Tools
            </h3>
            <div className="space-y-2">
              {/* AWS Connection */}
              <div className={`p-3 rounded-xl border flex flex-col gap-3 transition-colors ${awsConnected ? 'bg-green-500/5 border-green-500/20' : 'bg-gray-800/20 border-white/5 hover:border-blue-500/30'}`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className={`w-7 h-7 rounded-lg flex items-center justify-center ${awsConnected ? 'bg-green-500/10' : 'bg-gray-800'}`}>
                      <Database className={`w-4 h-4 ${awsConnected ? 'text-green-400' : 'text-gray-500'}`} />
                    </div>
                    <span className="text-xs font-semibold text-white">AWS</span>
                  </div>
                  {awsConnected ? (
                    <CheckCircle className="w-3.5 h-3.5 text-green-400" />
                  ) : (
                    <AlertCircle className="w-3.5 h-3.5 text-gray-600" />
                  )}
                </div>
                {!awsConnected && (
                  <button 
                    onClick={() => onOpenSettings("aws")}
                    className="w-full py-2 bg-blue-600/10 hover:bg-blue-600 text-blue-400 hover:text-white text-[10px] font-bold uppercase tracking-widest rounded-lg border border-blue-500/20 transition-all active:scale-[0.98]"
                  >
                    Connect AWS
                  </button>
                )}
              </div>

              {/* GitHub Connection */}
              <div className={`p-3 rounded-xl border flex flex-col gap-3 transition-colors ${githubConnected ? 'bg-green-500/5 border-green-500/20' : 'bg-gray-800/20 border-white/5 hover:border-purple-500/30'}`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className={`w-7 h-7 rounded-lg flex items-center justify-center ${githubConnected ? 'bg-green-500/10' : 'bg-gray-800'}`}>
                      <Github className={`w-4 h-4 ${githubConnected ? 'text-green-400' : 'text-gray-500'}`} />
                    </div>
                    <span className="text-xs font-semibold text-white">GitHub</span>
                  </div>
                  {githubConnected ? (
                    <CheckCircle className="w-3.5 h-3.5 text-green-400" />
                  ) : (
                    <AlertCircle className="w-3.5 h-3.5 text-gray-600" />
                  )}
                </div>
                {!githubConnected && (
                  <button 
                    onClick={() => onOpenSettings("repos")}
                    className="w-full py-2 bg-purple-600/10 hover:bg-purple-600 text-purple-400 hover:text-white text-[10px] font-bold uppercase tracking-widest rounded-lg border border-purple-500/20 transition-all active:scale-[0.98]"
                  >
                    Connect Repos
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {isCollapsed && <div className="flex-1" />}

      {/* User / Footer */}
      <div className={`p-4 border-t border-white/5 flex flex-col items-center gap-4 ${isCollapsed ? 'pb-8' : 'space-y-3'}`}>
        <button 
            onClick={() => onOpenSettings()}
            className={`flex items-center gap-3 text-gray-400 hover:text-white hover:bg-white/5 rounded-lg transition-colors group ${isCollapsed ? 'p-2 justify-center w-10 h-10' : 'w-full px-3 py-2'}`}
            title={isCollapsed ? "Global Settings" : undefined}
        >
            <Settings className={`w-5 h-5 group-hover:rotate-45 transition-transform duration-500 shrink-0 ${isCollapsed ? 'text-gray-400' : 'w-4 h-4'}`} />
            {!isCollapsed && <span className="text-xs font-medium animate-in fade-in duration-500">Global Settings</span>}
        </button>
        
        <button
            onClick={onLogout}
            className={`flex items-center gap-3 text-gray-500 hover:text-red-400 hover:bg-red-500/5 rounded-lg transition-colors group ${isCollapsed ? 'p-2 justify-center w-10 h-10' : 'w-full px-3 py-2'}`}
            title={isCollapsed ? "Log Out" : undefined}
        >
            <LogOut className={`w-5 h-5 group-hover:scale-110 transition-transform shrink-0 ${isCollapsed ? 'text-gray-500' : 'w-4 h-4'}`} />
            {!isCollapsed && <span className="text-xs font-medium animate-in fade-in duration-500">Log Out</span>}
        </button>

        {!isCollapsed && (
          <div className="flex items-center gap-3 w-full bg-white/[0.02] border border-white/5 rounded-xl p-3 animate-in fade-in duration-500">
              {user?.picture ? (
                  <img src={user.picture} alt={user?.name || "User"} className="w-8 h-8 rounded-full border border-white/10 ring-2 ring-blue-500/20" />
              ) : (
                  <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-[10px] font-bold text-white shadow-lg shadow-blue-500/20">
                      {user?.name?.charAt(0)?.toUpperCase() || "U"}
                  </div>
              )}
              <div className="truncate">
                  <p className="text-xs font-bold text-white truncate">{user?.name || "User"}</p>
                  <p className="text-[10px] text-gray-500 truncate">{user?.email || "Account Active"}</p>
              </div>
          </div>
        )}
      </div>
    </aside>
  );
}
