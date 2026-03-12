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

function getAuthHeaders(): Record<string, string> {
  const token = localStorage.getItem("opscribe_token");
  if (token) {
    return { Authorization: `Bearer ${token}` };
  }
  return {};
}

async function request<T>(
  path: string,
  options: RequestInit & { parseJson?: boolean } = {},
): Promise<T> {
  const { parseJson = true, ...init } = options;
  const url = path.startsWith("http")
    ? path
    : `${BASE.replace(/\/$/, "")}/${path.replace(/^\//, "")}`;
  const res = await fetch(url, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
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

  async setupAccount(data: { client_name: string; user_email: string; user_full_name: string; sso_domain?: string }): Promise<any> {
    return request<any>("auth/setup", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async loginById(clientId: string): Promise<any> {
    return request<any>(`auth/login?client_id=${clientId}`, {
      method: "POST",
    });
  },

  getSSOLoginUrl(): string {
    return `${BASE.replace(/\/$/, "")}/auth/sso/login`;
  },
};
