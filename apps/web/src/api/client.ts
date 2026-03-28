/**
 * API client for Opscribe backend.
 * Set VITE_API_URL (e.g. /api or http://localhost:8000) when not using nginx proxy.
 */

import type {
  ClientRead,
  GraphRead,
  GraphVisualization,
} from "../types/apiFormat";

const BASE =
  (import.meta as unknown as { env: { VITE_API_URL?: string } }).env
    ?.VITE_API_URL ?? "/api";

let globalToken: string | null = null;

export const setApiToken = (token: string | null) => {
  globalToken = token;
};

export const authFetch = async (input: RequestInfo | URL, init?: RequestInit) => {
  return fetch(input, {
    ...init,
    headers: {
      ...init?.headers,
      ...(globalToken ? { Authorization: `Bearer ${globalToken}` } : {})
    }
  });
};

async function request<T>(
  path: string,
  options: RequestInit & { parseJson?: boolean } = {},
): Promise<T> {
  const { parseJson = true, ...init } = options;
  const url = path.startsWith("http")
    ? path
    : `${BASE.replace(/\/$/, "")}/${path.replace(/^\//, "")}`;
  const res = await authFetch(url, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(init.headers as Record<string, string>),
    },
  });
  if (!res.ok) {
    const err = (await res.json().catch(() => ({}))) as { detail?: string };
    throw new Error(err.detail ?? res.statusText ?? `HTTP ${res.status}`);
  }
  if (parseJson) return (await res.json()) as T;
  return undefined as T;
}

export const api = {
  async getCurrentUser(): Promise<ClientRead> {
    return request<ClientRead>("clients/me");
  },

  async listGraphs(clientId: string): Promise<GraphRead[]> {
    return request<GraphRead[]>(`clients/${clientId}/graphs`);
  },

  async createGraph(clientId: string, name: string): Promise<GraphRead> {
    return request<GraphRead>("graphs/", {
      method: "POST",
      body: JSON.stringify({
        client_id: clientId,
        name,
        description: null,
        settings: {},
      }),
    });
  },

  async getGraph(graphId: string): Promise<GraphRead> {
    return request<GraphRead>(`graphs/${graphId}`);
  },

  async getVisualization(graphId: string): Promise<GraphVisualization> {
    return request<GraphVisualization>(`graphs/${graphId}/visualize`);
  },

  async syncGraph(
    graphId: string,
    body: {
      name?: string;
      nodes: Array<{
        id: string;
        type: string;
        position: { x: number; y: number };
        data: Record<string, unknown>;
      }>;
      edges: Array<{
        id: string;
        source: string;
        target: string;
        sourceHandle?: string;
        targetHandle?: string;
      }>;
    },
  ): Promise<GraphRead> {
    return request<GraphRead>(`graphs/${graphId}/sync`, {
      method: "PUT",
      body: JSON.stringify(body),
    });
  },

  async deleteGraph(graphId: string): Promise<void> {
    await request(`graphs/${graphId}`, { method: "DELETE", parseJson: false });
  },

  async ingestRepo(
    tenantId: string,
    repoUrl: string,
    ref: string = "main",
  ): Promise<{ status: string; chunks_ingested: number }> {
    return request<{ status: string; chunks_ingested: number }>("rag/ingest/repo", {
      method: "POST",
      body: JSON.stringify({ tenant_id: tenantId, repo_url: repoUrl, ref }),
    });
  },

  async ingestGraph(
    graphId: string,
  ): Promise<{ status: string; entities_ingested: number }> {
    return request<{ status: string; entities_ingested: number }>("rag/ingest/graph", {
      method: "POST",
      body: JSON.stringify({ graph_id: graphId }),
    });
  },

  async queryRag(
    tenantId: string,
    query: string,
    graphId?: string,
    limit: number = 5,
  ): Promise<{ items: any[]; answer: string }> {
    return request<{ items: any[]; answer: string }>("rag/query", {
      method: "POST",
      body: JSON.stringify({ tenant_id: tenantId, query, limit, ...(graphId ? { graph_id: graphId } : {}) }),
    });
  },
};
