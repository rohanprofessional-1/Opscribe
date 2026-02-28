import { useState, useCallback } from "react";
import InfrastructureDashboard from "./components/InfrastructureDashboard";
import InfrastructureDesigner from "./components/InfrastructureDesigner";
import { useInfrastructureDesigns } from "./hooks/useInfrastructureDesigns";
import type { Node, Edge } from "reactflow";
import type { InfrastructureNodeData } from "./types/infrastructure";
import "./App.css";

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
  const [activeDesignId, setActiveDesignId] = useState<string | null>(null);
  const [createPending, setCreatePending] = useState(false);

  const handleCreateNew = useCallback(() => {
    setCreatePending(true);
    createDesignAsync()
      .then((design) => setActiveDesignId(design.id))
      .finally(() => setCreatePending(false));
  }, [createDesignAsync]);

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

  if (activeDesignId) {
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
