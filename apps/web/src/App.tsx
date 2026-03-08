import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import LandingPage from "./components/LandingPage";
import SetupPage from "./components/SetupPage";
import LoginPage from "./components/LoginPage";
import InfrastructureDashboard from "./components/InfrastructureDashboard";
import InfrastructureDesigner from "./components/InfrastructureDesigner";
import { useInfrastructureDesigns } from "./hooks/useInfrastructureDesigns";
import { useAuth } from "./hooks/useAuth";
import { useState, useCallback } from "react";
import type { Node, Edge } from "reactflow";
import type { InfrastructureNodeData } from "./types/infrastructure";
import "./App.css";

const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) return <div className="min-h-screen bg-slate-900 flex items-center justify-center text-white">Loading...</div>;
  if (!isAuthenticated) return <Navigate to="/login" replace />;

  return <>{children}</>;
};

function App() {
  const {
    designs,
    loading,
    error,
    createDesignAsync,
    updateDesign,
    deleteDesign,
    getDesign,
  } = useInfrastructureDesigns();
  const { user } = useAuth();
  const [activeDesignId, setActiveDesignId] = useState<string | null>(null);
  const [createPending, setCreatePending] = useState(false);

  const handleCreateNew = useCallback(() => {
    if (!user) return;
    setCreatePending(true);
    createDesignAsync()
      .then((design) => setActiveDesignId(design.id))
      .finally(() => setCreatePending(false));
  }, [createDesignAsync, user]);

  const handleOpenDesign = useCallback((id: string) => {
    setActiveDesignId(id);
  }, []);

  const handleBack = useCallback(
    (
      nodes: Node<InfrastructureNodeData>[],
      edges: Edge[],
      name: string
    ) => {
      if (activeDesignId) {
        updateDesign(activeDesignId, { nodes, edges, name });
      }
      setActiveDesignId(null);
    },
    [activeDesignId, updateDesign]
  );

  const activeDesign = activeDesignId ? getDesign(activeDesignId) : null;

  return (
    <Router>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/setup" element={<SetupPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              {activeDesignId ? (
                <InfrastructureDesigner
                  design={activeDesign ?? { id: activeDesignId, name: "Untitled Infrastructure", updatedAt: new Date().toISOString(), nodes: [], edges: [] }}
                  onBack={handleBack}
                />
              ) : (
                <InfrastructureDashboard
                  designs={designs}
                  loading={loading}
                  error={error}
                  createPending={createPending}
                  onCreateNew={handleCreateNew}
                  onOpenDesign={handleOpenDesign}
                  onDeleteDesign={deleteDesign}
                />
              )}
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}

export default App;
