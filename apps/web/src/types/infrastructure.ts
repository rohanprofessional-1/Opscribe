// Types of Nodes
export type NodeCategory =
  | "database"
  | "compute"
  | "storage"
  | "networking"
  | "security"
  | "messaging";

// Base node information
export interface BaseNodeData {
  label: string;
  category: NodeCategory;
  icon: string;
  description?: string;
}

// Database node speific information
export interface DatabaseNodeData extends BaseNodeData {
  category: "database";
  dbType?: "sql" | "nosql" | "warehouse" | "cache";
  readWriteRelationship?: "read-only" | "write-only" | "read-write";
  owner?: string;
  replicationEnabled?: boolean;
  replicationFactor?: number;
  backupSchedule?: string;
}

// Compute node specific information
export interface ComputeNodeData extends BaseNodeData {
  category: "compute";
  instanceType?: string;
  cpu?: number;
  memory?: number;
  autoScaling?: boolean;
  minInstances?: number;
  maxInstances?: number;
}

// Storage node specific information
export interface StorageNodeData extends BaseNodeData {
  category: "storage";
  storageType?: "block" | "object" | "file";
  capacity?: number;
  encryption?: boolean;
  redundancy?: "single" | "replicated" | "distributed";
}

// Networking node specific information
export interface NetworkingNodeData extends BaseNodeData {
  category: "networking";
  networkType?: "vpc" | "subnet" | "load-balancer" | "cdn" | "dns";
  cidr?: string;
  publicAccess?: boolean;
  protocol?: "http" | "https" | "tcp" | "udp";
}

// Security node specific information
export interface SecurityNodeData extends BaseNodeData {
  category: "security";
  securityType?: "firewall" | "waf" | "iam" | "secrets" | "certificate";
  rules?: string[];
  encryption?: "aes-256" | "rsa-2048" | "none";
}

// Messaging node specific information
export interface MessagingNodeData extends BaseNodeData {
  category: "messaging";
  messagingType?: "queue" | "topic" | "stream" | "event-bus";
  retention?: number;
  throughput?: number;
  ordering?: boolean;
}

// Union type for all node information
export type InfrastructureNodeData =
  | DatabaseNodeData
  | ComputeNodeData
  | StorageNodeData
  | NetworkingNodeData
  | SecurityNodeData
  | MessagingNodeData;

// Node template for the palette
export interface NodeTemplate {
  id: string;
  type: string;
  label: string;
  category: NodeCategory;
  icon: string;
  description?: string;
  defaultData: Partial<InfrastructureNodeData>;
}

// Category configuration
export interface CategoryConfig {
  id: NodeCategory;
  label: string;
  icon: string;
  color: string;
}
