import { useState, useCallback } from "react";
import InfrastructureDashboard from "./components/InfrastructureDashboard";
import InfrastructureDesigner from "./components/InfrastructureDesigner";
import LandingPage from "./components/landing/LandingPage";
import LoginPage from "./components/LoginPage";
import SignUpPage from "./components/SignUpPage";
import { useInfrastructureDesigns } from "./hooks/useInfrastructureDesigns";
import type { Node, Edge } from "reactflow";
import type { InfrastructureNodeData } from "./types/infrastructure";
import "./App.css";

type View = "landing" | "login" | "signup" | "dashboard" | "designer";

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
  
  const [view, setView] = useState<View>("landing");
  const [activeDesignId, setActiveDesignId] = useState<string | null>(null);
  const [createPending, setCreatePending] = useState(false);

  const handleCreateNew = useCallback(() => {
    setCreatePending(true);
    createDesignAsync()
      .then((design) => {
        setActiveDesignId(design.id);
        setView("designer");
      })
      .finally(() => setCreatePending(false));
  }, [createDesignAsync]);

  const handleOpenDesign = useCallback((id: string) => {
    setActiveDesignId(id);
    setView("designer");
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
      setView("dashboard");
    },
    [activeDesignId, updateDesign]
  );

  const activeDesign = activeDesignId ? getDesign(activeDesignId) : null;

  if (view === "designer" && activeDesignId) {
    return (
      <InfrastructureDesigner
        design={activeDesign ?? { id: activeDesignId, name: "Untitled Infrastructure", updatedAt: new Date().toISOString(), nodes: [], edges: [] }}
        onBack={handleBack}
      />
    );
  }

  if (view === "landing") {
    return (
      <LandingPage 
        onLaunch={() => setView("signup")} 
        onLogin={() => setView("login")}
      />
    );
  }

  if (view === "login") {
    return (
      <LoginPage 
        onLogin={() => setView("dashboard")} 
        onBackToLanding={() => setView("landing")}
        onGoToSignup={() => setView("signup")}
      />
    );
  }

  if (view === "signup") {
    return (
      <SignUpPage 
        onSignUp={() => setView("dashboard")} 
        onBackToLanding={() => setView("landing")}
        onGoToLogin={() => setView("login")}
      />
    );
  }

  return (
    <InfrastructureDashboard
      designs={designs}
      loading={loading}
      error={error}
      createPending={createPending}
      onCreateNew={handleCreateNew}
      onOpenDesign={handleOpenDesign}
      onDeleteDesign={deleteDesign}
    />
  );
}

export default App;
