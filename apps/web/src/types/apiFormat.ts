export interface ClientRead {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
  metadata_?: Record<string, unknown>;
}

export interface GraphRead {
  id: string;
  client_id: string;
  name: string;
  description?: string | null;
  settings?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface NodeRead {
  id: string;
  key: string;
  display_name?: string | null;
  properties: Record<string, unknown>;
  graph_id: string;
  node_type_id: string;
  client_id: string;
  created_at: string;
  updated_at: string;
}

export interface EdgeRead {
  id: string;
  from_node_id: string;
  to_node_id: string;
  graph_id: string;
  edge_type_id: string;
  client_id: string;
  properties?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface GraphVisualization {
  nodes: NodeRead[];
  edges: EdgeRead[];
}
