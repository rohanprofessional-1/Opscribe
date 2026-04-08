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
    const persona = (data as any).persona || "engineer";
    const stability = (data as any).stability || 0;
    const techDebt = (data as any).tech_debt || 0;
    const criticality = (data as any).criticality || "medium";

    const isPM = persona === "pm";

    // ENGINEER VIEW: Pristine Original Style
    if (!isPM) {
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
    }

    // PRODUCT MANAGER VIEW: Strategic Enhanced Style
    return (
      <div
        className={`
          relative rounded-xl border-2 shadow-2xl transition-all duration-300
          min-w-[180px] group bg-gray-900/40 backdrop-blur-md border-opacity-50
          ${selected ? "ring-2 ring-blue-500 ring-offset-4 ring-offset-gray-900 scale-105 shadow-blue-900/30" : "shadow-black/50"}
          ${criticality === "high" ? "shadow-[0_0_20px_rgba(59,130,246,0.3)] animate-pulse-slow font-bold" : ""}
        `}
        style={{ borderColor: categoryColor }}
      >
        {/* Stability Health Bar */}
        <div className="absolute -top-3 left-1/2 -translate-x-1/2 w-[80%] h-1.5 bg-gray-800 rounded-full overflow-hidden border border-gray-700 shadow-inner">
           <div 
              className={`h-full transition-all duration-1000 ${stability > 80 ? 'bg-green-500' : stability > 50 ? 'bg-yellow-500' : 'bg-red-500'}`}
              style={{ width: `${stability}%` }}
           />
        </div>

        <Handle
          type="source"
          position={Position.Right}
          className="!w-3 !h-3 !bg-gray-600 !border-2 !border-gray-400 hover:!bg-blue-500 hover:!border-blue-400 transition-colors"
        />

        <div className="p-4">
          <div className="flex items-center gap-3">
            <div
              className="p-2.5 rounded-lg transition-transform duration-300 group-hover:rotate-12 shadow-lg shadow-black/50"
              style={{ backgroundColor: `${categoryColor}20` }}
            >
              {IconComponent && (
                <IconComponent
                  size={24}
                  className="text-white"
                  style={{ color: categoryColor }}
                />
              )}
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-bold text-white truncate text-base tracking-tight">
                {data.label}
              </p>
              <div className="flex items-center gap-2">
                <p className="text-[10px] text-gray-400 uppercase font-black tracking-widest leading-none">
                    {data.category}
                </p>
                {techDebt > 50 && (
                   <span className="flex items-center gap-0.5 text-[9px] font-black bg-red-900/50 text-red-400 px-1.5 py-0.5 rounded border border-red-800/50 animate-bounce-subtle">
                      DEBT: {techDebt}%
                   </span>
                )}
              </div>
            </div>
          </div>

          {/* Strategic Insights Footer */}
          <div className="mt-4 pt-3 border-t border-white/5 flex items-center justify-between">
              <div className="flex flex-col">
                  <span className="text-[8px] text-gray-500 font-black uppercase tracking-tighter">Strategic Impact</span>
                  <span className="text-[10px] font-bold text-blue-300">{criticality === 'high' ? 'Critical' : 'Supporting'}</span>
              </div>
              <div className="flex flex-col text-right">
                  <span className="text-[8px] text-gray-500 font-black uppercase tracking-tighter">Stability</span>
                  <span className={`text-[10px] font-bold ${stability > 80 ? 'text-green-400' : 'text-yellow-400'}`}>{stability}%</span>
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
