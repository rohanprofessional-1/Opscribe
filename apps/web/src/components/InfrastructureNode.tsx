/**
 * This component is the infrastructure node for the infrastructure design
 * and will be on the canvas.
 * It displays the node and allows the user to drag and drop it onto the canvas.
 * It also allows the user to select the node and edit its properties.
 */

import { memo } from "react";
import { Handle, Position } from "reactflow";
import type { NodeProps } from "reactflow";
import * as Icons from "lucide-react";
import { getCategoryColor } from "../data/nodeTemplates.ts";
import type { InfrastructureNodeData } from "../types/infrastructure.ts";

type IconName = keyof typeof Icons;

const InfrastructureNode = memo(
  ({ data, selected }: NodeProps<InfrastructureNodeData>) => {
    const IconComponent = Icons[data.icon as IconName] as React.ComponentType<{
      size?: number;
      className?: string;
      style?: React.CSSProperties;
    }>;
    const categoryColor = getCategoryColor(data.category);

    return (
      <div
        className={`
        relative bg-gray-800 rounded-lg border-2 shadow-lg
        min-w-[140px] transition-all duration-200
        ${selected ? "ring-2 ring-blue-500 ring-offset-2 ring-offset-gray-900" : ""}
      `}
        style={{ borderColor: categoryColor }}
      >
        <Handle
          type="source"
          position={Position.Right}
          className="!w-3 !h-3 !bg-gray-600 !border-2 !border-gray-400 hover:!bg-blue-500 hover:!border-blue-400 transition-colors"
        />

        <div className="p-3">
          <div className="flex items-center gap-2">
            <div
              className="p-2 rounded-md"
              style={{ backgroundColor: `${categoryColor}20` }}
            >
              {IconComponent && (
                <IconComponent
                  size={20}
                  className="text-white"
                  style={{ color: categoryColor }}
                />
              )}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-white truncate">
                {data.label}
              </p>
              <p className="text-xs text-gray-400 capitalize">
                {data.category}
              </p>
            </div>
          </div>
        </div>

        <Handle
          type="target"
          position={Position.Left}
          className="!w-3 !h-3 !bg-gray-600 !border-2 !border-gray-400 hover:!bg-blue-500 hover:!border-blue-400 transition-colors"
        />
      </div>
    );
  },
);

InfrastructureNode.displayName = "InfrastructureNode";

export default InfrastructureNode;
