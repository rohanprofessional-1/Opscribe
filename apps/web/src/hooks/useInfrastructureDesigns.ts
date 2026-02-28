import { useState, useCallback, useEffect } from "react";
import type { InfrastructureDesign } from "../types/infrastructure";
import type { Node, Edge } from "reactflow";
import { api } from "../api/client";

function graphToDesign(g: {
  id: string;
  name: string;
  updated_at: string;
}): InfrastructureDesign {
  return {
    id: g.id,
    name: g.name,
    updatedAt: g.updated_at,
    nodes: [],
    edges: [],
  };
}

export function useInfrastructureDesigns() {
  const [clientId, setClientId] = useState<string | null>(null);
  const [designs, setDesigns] = useState<InfrastructureDesign[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    api
      .getAnonSession()
      .then((client) => {
        if (cancelled) return;
        setClientId(client.id);
        return api.listGraphs(client.id);
      })
      .then((graphs) => {
        if (cancelled || graphs === undefined) return;
        setDesigns(graphs.map(graphToDesign));
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const createDesignAsync = useCallback((): Promise<InfrastructureDesign> => {
    if (!clientId) return Promise.reject(new Error("Client not loaded"));

    return api.createGraph(clientId, "Untitled Infrastructure").then((g) => {
      const d = graphToDesign(g);
      setDesigns((prev) => [d, ...prev]);
      return d;
    });
  }, [clientId]);

  const updateDesign = useCallback(
    (id: string, updates: { name?: string; nodes: Node[]; edges: Edge[] }) => {
      api
        .syncGraph(id, {
          name: updates.name,
          nodes: updates.nodes.map((n) => ({
            id: n.id,
            type: n.type ?? "infrastructureNode",
            position: n.position,
            data: (n.data ?? {}) as Record<string, unknown>,
          })),
          edges: updates.edges.map((e) => ({
            id: e.id,
            source: e.source,
            target: e.target,
            sourceHandle: e.sourceHandle ?? undefined,
            targetHandle: e.targetHandle ?? undefined,
          })),
        })
        .then((g) => {
          setDesigns((prev) =>
            prev.map((d) =>
              d.id === id ? { ...d, name: g.name, updatedAt: g.updated_at } : d,
            ),
          );
        })
        .catch((e) => setError(e instanceof Error ? e.message : String(e)));
    },
    [],
  );

  const deleteDesign = useCallback((id: string) => {
    api
      .deleteGraph(id)
      .then(() => setDesigns((prev) => prev.filter((d) => d.id !== id)))
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  const getDesign = useCallback(
    (id: string) => designs.find((d) => d.id === id),
    [designs],
  );

  return {
    clientId,
    designs,
    loading,
    error,
    createDesignAsync,
    updateDesign,
    deleteDesign,
    getDesign,
  };
}
