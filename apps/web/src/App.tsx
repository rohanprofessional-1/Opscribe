import { useState, useCallback, useEffect } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import { setApiToken } from "./api/client";
import InfrastructureDashboard from "./components/InfrastructureDashboard";
import InfrastructureDesigner from "./components/InfrastructureDesigner";
import LandingPage from "./components/landing/LandingPage";
import { useInfrastructureDesigns } from "./hooks/useInfrastructureDesigns";
import type { Node, Edge } from "reactflow";
import type { InfrastructureNodeData } from "./types/infrastructure";
import "./App.css";

type View = "dashboard" | "designer";

function App() {
  const { isLoading, isAuthenticated, loginWithRedirect, getAccessTokenSilently } = useAuth0();
  const [tokenReady, setTokenReady] = useState(false);

  useEffect(() => {
    if (isAuthenticated) {
      getAccessTokenSilently()
        .then(token => {
          setApiToken(token);
          setTokenReady(true);
        })
        .catch(err => console.error("Auth0 Token Error:", err));
    } else if (!isLoading) {
      setTokenReady(true);
    }
  }, [isAuthenticated, isLoading, getAccessTokenSilently]);

  const {
    designs,
    loading: designsLoading,
    error,
    createDesignAsync,
    updateDesign,
    deleteDesign,
    getDesign,
  } = useInfrastructureDesigns(tokenReady);

  const [view, setView] = useState<View>("dashboard");
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

  if (isLoading || !tokenReady) {
    return (
      <div className="min-h-screen bg-[#0A0D14] flex items-center justify-center text-gray-400 font-mono text-sm">
        Authenticating...
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <LandingPage
        onLaunch={() => loginWithRedirect({ authorizationParams: { screen_hint: "signup" } })}
        onLogin={() => loginWithRedirect()}
      />
    );
  }

  if (view === "designer" && activeDesignId) {
    return (
      <InfrastructureDesigner
        design={activeDesign ?? { id: activeDesignId, name: "Untitled Infrastructure", updatedAt: new Date().toISOString(), nodes: [], edges: [] }}
        onBack={handleBack}
      />
    );
  }

  return (
    <InfrastructureDashboard
      designs={designs}
      loading={designsLoading}
      error={error}
      createPending={createPending}
      onCreateNew={handleCreateNew}
      onOpenDesign={handleOpenDesign}
      onDeleteDesign={deleteDesign}
    />
  );
}

export default App;
