import type { Node } from "reactflow";
import * as Icons from "lucide-react";
import { X, Trash2 } from "lucide-react";
import { getCategoryColor } from "../data/nodeTemplates.ts";
import type {
  InfrastructureNodeData,
  NodeCategory,
} from "../types/infrastructure";

type IconName = keyof typeof Icons;

interface PropertiesPanelProps {
  selectedNode: Node<InfrastructureNodeData> | null;
  onUpdateNode: (nodeId: string, data: Partial<InfrastructureNodeData>) => void;
  onDeleteNode: (nodeId: string) => void;
  onClose: () => void;
}

export default function PropertiesPanel({
  selectedNode,
  onUpdateNode,
  onDeleteNode,
  onClose,
}: PropertiesPanelProps) {
  if (!selectedNode) {
    return (
      <div className="w-80 bg-gray-900 border-l border-gray-700 flex flex-col h-full">
        <div className="flex-1 flex items-center justify-center p-6">
          <div className="text-center">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gray-800 flex items-center justify-center">
              <Icons.MousePointer2 className="w-8 h-8 text-gray-500" />
            </div>
            <p className="text-gray-400 text-sm">
              Select a node to view its properties
            </p>
          </div>
        </div>
      </div>
    );
  }

  const { data, id } = selectedNode;
  const IconComponent = Icons[data.icon as IconName] as React.ComponentType<{
    size?: number;
    className?: string;
    style?: React.CSSProperties;
  }>;
  const categoryColor = getCategoryColor(data.category);

  const handleChange = (field: string, value: string | number | boolean) => {
    onUpdateNode(id, { [field]: value } as Partial<InfrastructureNodeData>);
  };

  const renderCategoryFields = () => {
    switch (data.category as NodeCategory) {
      case "database":
        return (
          <>
            <FormField label="Database Type">
              <select
                value={(data as any).dbType || ""}
                onChange={(e) => handleChange("dbType", e.target.value)}
                className="form-select"
              >
                <option value="">Select type...</option>
                <option value="sql">SQL</option>
                <option value="nosql">NoSQL</option>
                <option value="warehouse">Data Warehouse</option>
                <option value="cache">Cache</option>
              </select>
            </FormField>

            <FormField label="Read/Write Relationship">
              <select
                value={(data as any).readWriteRelationship || ""}
                onChange={(e) =>
                  handleChange("readWriteRelationship", e.target.value)
                }
                className="form-select"
              >
                <option value="">Select...</option>
                <option value="read-only">Read Only</option>
                <option value="write-only">Write Only</option>
                <option value="read-write">Read/Write</option>
              </select>
            </FormField>

            <FormField label="Owner">
              <input
                type="text"
                value={(data as any).owner || ""}
                onChange={(e) => handleChange("owner", e.target.value)}
                placeholder="Enter owner name..."
                className="form-input"
              />
            </FormField>

            <FormField label="Replication">
              <div className="flex items-center gap-3">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={(data as any).replicationEnabled || false}
                    onChange={(e) =>
                      handleChange("replicationEnabled", e.target.checked)
                    }
                    className="form-checkbox"
                  />
                  <span className="text-sm text-gray-300">Enabled</span>
                </label>
              </div>
            </FormField>

            {(data as any).replicationEnabled && (
              <FormField label="Replication Factor">
                <input
                  type="number"
                  min={1}
                  max={10}
                  value={(data as any).replicationFactor || 3}
                  onChange={(e) =>
                    handleChange("replicationFactor", parseInt(e.target.value))
                  }
                  className="form-input"
                />
              </FormField>
            )}

            <FormField label="Backup Schedule">
              <input
                type="text"
                value={(data as any).backupSchedule || ""}
                onChange={(e) => handleChange("backupSchedule", e.target.value)}
                placeholder="e.g., 0 2 * * *"
                className="form-input"
              />
            </FormField>
          </>
        );

      case "compute":
        return (
          <>
            <FormField label="Instance Type">
              <select
                value={(data as any).instanceType || ""}
                onChange={(e) => handleChange("instanceType", e.target.value)}
                className="form-select"
              >
                <option value="">Select type...</option>
                <option value="standard">Standard</option>
                <option value="compute-optimized">Compute Optimized</option>
                <option value="memory-optimized">Memory Optimized</option>
                <option value="container">Container</option>
                <option value="serverless">Serverless</option>
                <option value="kubernetes">Kubernetes</option>
              </select>
            </FormField>

            <FormField label="CPU (vCPUs)">
              <input
                type="number"
                min={1}
                max={128}
                value={(data as any).cpu || 2}
                onChange={(e) => handleChange("cpu", parseInt(e.target.value))}
                className="form-input"
              />
            </FormField>

            <FormField label="Memory (GB)">
              <input
                type="number"
                min={1}
                max={512}
                value={(data as any).memory || 4}
                onChange={(e) =>
                  handleChange("memory", parseInt(e.target.value))
                }
                className="form-input"
              />
            </FormField>

            <FormField label="Auto Scaling">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={(data as any).autoScaling || false}
                  onChange={(e) =>
                    handleChange("autoScaling", e.target.checked)
                  }
                  className="form-checkbox"
                />
                <span className="text-sm text-gray-300">Enabled</span>
              </label>
            </FormField>

            {(data as any).autoScaling && (
              <>
                <FormField label="Min Instances">
                  <input
                    type="number"
                    min={1}
                    value={(data as any).minInstances || 1}
                    onChange={(e) =>
                      handleChange("minInstances", parseInt(e.target.value))
                    }
                    className="form-input"
                  />
                </FormField>
                <FormField label="Max Instances">
                  <input
                    type="number"
                    min={1}
                    value={(data as any).maxInstances || 10}
                    onChange={(e) =>
                      handleChange("maxInstances", parseInt(e.target.value))
                    }
                    className="form-input"
                  />
                </FormField>
              </>
            )}
          </>
        );

      case "storage":
        return (
          <>
            <FormField label="Storage Type">
              <select
                value={(data as any).storageType || ""}
                onChange={(e) => handleChange("storageType", e.target.value)}
                className="form-select"
              >
                <option value="">Select type...</option>
                <option value="block">Block Storage</option>
                <option value="object">Object Storage</option>
                <option value="file">File Storage</option>
              </select>
            </FormField>

            <FormField label="Capacity (GB)">
              <input
                type="number"
                min={1}
                value={(data as any).capacity || 100}
                onChange={(e) =>
                  handleChange("capacity", parseInt(e.target.value))
                }
                className="form-input"
              />
            </FormField>

            <FormField label="Encryption">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={(data as any).encryption || false}
                  onChange={(e) => handleChange("encryption", e.target.checked)}
                  className="form-checkbox"
                />
                <span className="text-sm text-gray-300">Enabled</span>
              </label>
            </FormField>

            <FormField label="Redundancy">
              <select
                value={(data as any).redundancy || ""}
                onChange={(e) => handleChange("redundancy", e.target.value)}
                className="form-select"
              >
                <option value="">Select...</option>
                <option value="single">Single</option>
                <option value="replicated">Replicated</option>
                <option value="distributed">Distributed</option>
              </select>
            </FormField>
          </>
        );

      case "networking":
        return (
          <>
            <FormField label="Network Type">
              <select
                value={(data as any).networkType || ""}
                onChange={(e) => handleChange("networkType", e.target.value)}
                className="form-select"
              >
                <option value="">Select type...</option>
                <option value="vpc">VPC</option>
                <option value="subnet">Subnet</option>
                <option value="load-balancer">Load Balancer</option>
                <option value="cdn">CDN</option>
                <option value="dns">DNS</option>
              </select>
            </FormField>

            <FormField label="CIDR Block">
              <input
                type="text"
                value={(data as any).cidr || ""}
                onChange={(e) => handleChange("cidr", e.target.value)}
                placeholder="e.g., 10.0.0.0/16"
                className="form-input"
              />
            </FormField>

            <FormField label="Protocol">
              <select
                value={(data as any).protocol || ""}
                onChange={(e) => handleChange("protocol", e.target.value)}
                className="form-select"
              >
                <option value="">Select...</option>
                <option value="http">HTTP</option>
                <option value="https">HTTPS</option>
                <option value="tcp">TCP</option>
                <option value="udp">UDP</option>
              </select>
            </FormField>

            <FormField label="Public Access">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={(data as any).publicAccess || false}
                  onChange={(e) =>
                    handleChange("publicAccess", e.target.checked)
                  }
                  className="form-checkbox"
                />
                <span className="text-sm text-gray-300">Enabled</span>
              </label>
            </FormField>
          </>
        );

      case "security":
        return (
          <>
            <FormField label="Security Type">
              <select
                value={(data as any).securityType || ""}
                onChange={(e) => handleChange("securityType", e.target.value)}
                className="form-select"
              >
                <option value="">Select type...</option>
                <option value="firewall">Firewall</option>
                <option value="waf">WAF</option>
                <option value="iam">IAM</option>
                <option value="secrets">Secrets Manager</option>
                <option value="certificate">Certificate</option>
              </select>
            </FormField>

            <FormField label="Encryption">
              <select
                value={(data as any).encryption || ""}
                onChange={(e) => handleChange("encryption", e.target.value)}
                className="form-select"
              >
                <option value="">Select...</option>
                <option value="aes-256">AES-256</option>
                <option value="rsa-2048">RSA-2048</option>
                <option value="none">None</option>
              </select>
            </FormField>
          </>
        );

      case "messaging":
        return (
          <>
            <FormField label="Messaging Type">
              <select
                value={(data as any).messagingType || ""}
                onChange={(e) => handleChange("messagingType", e.target.value)}
                className="form-select"
              >
                <option value="">Select type...</option>
                <option value="queue">Queue</option>
                <option value="topic">Topic</option>
                <option value="stream">Stream</option>
                <option value="event-bus">Event Bus</option>
              </select>
            </FormField>

            <FormField label="Retention (days)">
              <input
                type="number"
                min={1}
                max={365}
                value={(data as any).retention || 7}
                onChange={(e) =>
                  handleChange("retention", parseInt(e.target.value))
                }
                className="form-input"
              />
            </FormField>

            <FormField label="Throughput (msg/sec)">
              <input
                type="number"
                min={1}
                value={(data as any).throughput || 1000}
                onChange={(e) =>
                  handleChange("throughput", parseInt(e.target.value))
                }
                className="form-input"
              />
            </FormField>

            <FormField label="Message Ordering">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={(data as any).ordering || false}
                  onChange={(e) => handleChange("ordering", e.target.checked)}
                  className="form-checkbox"
                />
                <span className="text-sm text-gray-300">Preserve Order</span>
              </label>
            </FormField>
          </>
        );

      default:
        return null;
    }
  };

  return (
    <div className="w-80 bg-gray-900 border-l border-gray-700 flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-gray-700">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold text-white">Properties</h2>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-gray-800 transition-colors"
          >
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        {/* Node Info */}
        <div className="flex items-center gap-3 p-3 bg-gray-800 rounded-lg">
          <div
            className="p-2 rounded-md"
            style={{ backgroundColor: `${categoryColor}20` }}
          >
            {IconComponent && (
              <IconComponent size={24} style={{ color: categoryColor }} />
            )}
          </div>
          <div className="flex-1 min-w-0">
            <input
              type="text"
              value={data.label}
              onChange={(e) => handleChange("label", e.target.value)}
              className="w-full bg-transparent text-white font-medium focus:outline-none focus:ring-1 focus:ring-blue-500 rounded px-1 -ml-1"
            />
            <p className="text-xs text-gray-400 capitalize">{data.category}</p>
          </div>
        </div>
      </div>

      {/* Form Fields */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {renderCategoryFields()}
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-gray-700">
        <button
          onClick={() => onDeleteNode(id)}
          className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-red-900/30 text-red-400 rounded-md hover:bg-red-900/50 transition-colors"
        >
          <Trash2 className="w-4 h-4" />
          Delete Node
        </button>
      </div>
    </div>
  );
}

// Helper component for form fields
function FormField({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-400 mb-1.5">
        {label}
      </label>
      {children}
    </div>
  );
}
