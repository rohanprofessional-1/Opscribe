/**
 * This file creates a template for the types of categories and the nodes that
 * can be created for each category.
 *
 * Currently there are 6 categories: database, compute, storage, networking, security, and messaging.
 * Each category has a list of nodes that can be created for that category.
 * Each node has a list of properties, relationships, constraints, dependencies, and dependencies
 * that can be set for that node.
 */

import type { NodeTemplate, CategoryConfig } from "../types/infrastructure";

export const categories: CategoryConfig[] = [
  { id: "database", label: "Databases", icon: "Database", color: "#3b82f6" },
  { id: "compute", label: "Compute", icon: "Cpu", color: "#22c55e" },
  { id: "storage", label: "Storage", icon: "HardDrive", color: "#f59e0b" },
  { id: "networking", label: "Networking", icon: "Network", color: "#8b5cf6" },
  { id: "security", label: "Security", icon: "Shield", color: "#ef4444" },
  {
    id: "messaging",
    label: "Messaging",
    icon: "MessageSquare",
    color: "#06b6d4",
  },
];

export const getCategoryColor = (category: string): string => {
  const cat = categories.find((c) => c.id === category);
  return cat?.color || "#6b7280";
};

export const nodeTemplates: NodeTemplate[] = [
  // Database nodes
  {
    id: "sql-db",
    type: "infrastructureNode",
    label: "SQL Database",
    category: "database",
    icon: "Database",
    description: "Describe the database node",
    defaultData: {
      dbType: "sql",
      readWriteRelationship: "read-write",
      replicationEnabled: false,
    },
  },
  {
    id: "nosql-db",
    type: "infrastructureNode",
    label: "NoSQL Database",
    category: "database",
    icon: "Layers",
    description: "Describe the noSQL database node",
    defaultData: {
      dbType: "nosql",
      readWriteRelationship: "read-write",
      replicationEnabled: true,
    },
  },
  {
    id: "data-warehouse",
    type: "infrastructureNode",
    label: "Data Warehouse",
    category: "database",
    icon: "Warehouse",
    description: "Describe the data warehouse node",
    defaultData: {
      dbType: "warehouse",
      readWriteRelationship: "read-only",
    },
  },
  {
    id: "cache",
    type: "infrastructureNode",
    label: "Cache",
    category: "database",
    icon: "Zap",
    description: "Describe the cache node",
    defaultData: {
      dbType: "cache",
      readWriteRelationship: "read-write",
    },
  },

  // Compute nodes
  {
    id: "vm",
    type: "infrastructureNode",
    label: "Virtual Machine",
    category: "compute",
    icon: "Server",
    description: "Describe the virtual machine node",
    defaultData: {
      instanceType: "standard",
      cpu: 2,
      memory: 4,
      autoScaling: false,
    },
  },
  {
    id: "container",
    type: "infrastructureNode",
    label: "Container",
    category: "compute",
    icon: "Box",
    description: "Describe the container node",
    defaultData: {
      instanceType: "container",
      cpu: 1,
      memory: 2,
      autoScaling: true,
    },
  },
  {
    id: "serverless",
    type: "infrastructureNode",
    label: "Serverless Function",
    category: "compute",
    icon: "Cloud",
    description: "Describe the serverless function node",
    defaultData: {
      instanceType: "serverless",
      autoScaling: true,
    },
  },
  {
    id: "kubernetes",
    type: "infrastructureNode",
    label: "Kubernetes Cluster",
    category: "compute",
    icon: "Boxes",
    description: "Describe the kubernetes cluster node",
    defaultData: {
      instanceType: "kubernetes",
      autoScaling: true,
      minInstances: 3,
      maxInstances: 10,
    },
  },

  // Storage nodes
  {
    id: "block-storage",
    type: "infrastructureNode",
    label: "Block Storage",
    category: "storage",
    icon: "HardDrive",
    description: "Describe the block storage node",
    defaultData: {
      storageType: "block",
      encryption: true,
      redundancy: "replicated",
    },
  },
  {
    id: "object-storage",
    type: "infrastructureNode",
    label: "Object Storage",
    category: "storage",
    icon: "Archive",
    description: "Describe the object storage node",
    defaultData: {
      storageType: "object",
      encryption: true,
      redundancy: "distributed",
    },
  },
  {
    id: "file-storage",
    type: "infrastructureNode",
    label: "File Storage",
    category: "storage",
    icon: "FolderOpen",
    description: "Describe the file storage node",
    defaultData: {
      storageType: "file",
      encryption: false,
      redundancy: "replicated",
    },
  },

  // Networking nodes
  {
    id: "vpc",
    type: "infrastructureNode",
    label: "VPC",
    category: "networking",
    icon: "Network",
    description: "Describe the VPC node",
    defaultData: {
      networkType: "vpc",
      cidr: "10.0.0.0/16",
      publicAccess: false,
    },
  },
  {
    id: "load-balancer",
    type: "infrastructureNode",
    label: "Load Balancer",
    category: "networking",
    icon: "GitBranch",
    description: "Describe the load balancer node",
    defaultData: {
      networkType: "load-balancer",
      protocol: "https",
      publicAccess: true,
    },
  },
  {
    id: "cdn",
    type: "infrastructureNode",
    label: "CDN",
    category: "networking",
    icon: "Globe",
    description: "Describe the CDN node",
    defaultData: {
      networkType: "cdn",
      publicAccess: true,
    },
  },
  {
    id: "dns",
    type: "infrastructureNode",
    label: "DNS",
    category: "networking",
    icon: "AtSign",
    description: "Describe the DNS node",
    defaultData: {
      networkType: "dns",
      publicAccess: true,
    },
  },

  // Security nodes
  {
    id: "firewall",
    type: "infrastructureNode",
    label: "Firewall",
    category: "security",
    icon: "Shield",
    description: "Describe the firewall node",
    defaultData: {
      securityType: "firewall",
      rules: [],
    },
  },
  {
    id: "waf",
    type: "infrastructureNode",
    label: "WAF",
    category: "security",
    icon: "ShieldCheck",
    description: "Describe the WAF node",
    defaultData: {
      securityType: "waf",
    },
  },
  {
    id: "iam",
    type: "infrastructureNode",
    label: "IAM",
    category: "security",
    icon: "Users",
    description: "Describe the IAM node",
    defaultData: {
      securityType: "iam",
    },
  },
  {
    id: "secrets",
    type: "infrastructureNode",
    label: "Secrets Manager",
    category: "security",
    icon: "Key",
    description: "Describe the secrets manager node",
    defaultData: {
      securityType: "secrets",
      encryption: "aes-256",
    },
  },

  // Messaging nodes
  {
    id: "message-queue",
    type: "infrastructureNode",
    label: "Message Queue",
    category: "messaging",
    icon: "ListOrdered",
    description: "Describe the message queue node",
    defaultData: {
      messagingType: "queue",
      ordering: true,
    },
  },
  {
    id: "pub-sub",
    type: "infrastructureNode",
    label: "Pub/Sub Topic",
    category: "messaging",
    icon: "Radio",
    description: "Describe the pub/sub topic node",
    defaultData: {
      messagingType: "topic",
      ordering: false,
    },
  },
  {
    id: "event-stream",
    type: "infrastructureNode",
    label: "Event Stream",
    category: "messaging",
    icon: "Activity",
    description: "Describe the event stream node",
    defaultData: {
      messagingType: "stream",
      retention: 7,
      ordering: true,
    },
  },
  {
    id: "event-bus",
    type: "infrastructureNode",
    label: "Event Bus",
    category: "messaging",
    icon: "Share2",
    description: "Describe the event bus node",
    defaultData: {
      messagingType: "event-bus",
    },
  },
];
