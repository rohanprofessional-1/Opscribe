/**
 * This component is the node palette for the infrastructure design
 * and will be on the right side of the canvas.
 * It displays the categories and nodes that can be created for each category
 * and allows the user to drag and drop nodes onto the canvas.
 */

import { useState } from "react";
import * as Icons from "lucide-react";
import { ChevronDown, ChevronRight, GripVertical, Search } from "lucide-react";
import {
  categories,
  nodeTemplates,
  getCategoryColor,
  getAnalogy,
} from "../data/nodeTemplates.ts";
import type { NodeCategory, NodeTemplate } from "../types/infrastructure.ts";

type IconName = keyof typeof Icons;

interface NodePaletteProps {
  onDragStart: (event: React.DragEvent, template: NodeTemplate) => void;
  persona: "pm" | "engineer";
}

export default function NodePalette({ onDragStart, persona }: NodePaletteProps) {
  const isPM = persona === "pm";
  const [expandedCategories, setExpandedCategories] = useState<
    Set<NodeCategory>
  >(new Set(categories.map((c) => c.id)));
  const [searchQuery, setSearchQuery] = useState("");

  const toggleCategory = (categoryId: NodeCategory) => {
    setExpandedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(categoryId)) {
        next.delete(categoryId);
      } else {
        next.add(categoryId);
      }
      return next;
    });
  };

  const filteredTemplates = searchQuery
    ? nodeTemplates.filter(
        (t) =>
          t.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
          t.category.toLowerCase().includes(searchQuery.toLowerCase()),
      )
    : nodeTemplates;

  const getTemplatesByCategory = (categoryId: NodeCategory) => {
    return filteredTemplates.filter((t) => t.category === categoryId);
  };

  return (
    <div className="w-64 bg-gray-900 border-r border-gray-700 flex flex-col h-full">
      <div className={`p-4 border-b border-gray-700 ${isPM ? 'bg-gray-900/80 backdrop-blur' : ''}`}>
        <h2 className="text-sm font-black uppercase tracking-widest text-gray-500 mb-3">
            {isPM ? "Strategic Components" : "Infrastructure Nodes"}
        </h2>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search nodes..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 bg-gray-800 border border-gray-600 rounded-md text-sm text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        {categories.map((category) => {
          const CategoryIcon = Icons[
            category.icon as IconName
          ] as React.ComponentType<{
            size?: number;
            className?: string;
            style?: React.CSSProperties;
          }>;

          const templates = getTemplatesByCategory(category.id);
          const isExpanded = expandedCategories.has(category.id);

          if (searchQuery && templates.length === 0) return null;

          return (
            <div key={category.id} className="mb-2">
              <button
                onClick={() => toggleCategory(category.id)}
                className="w-full flex items-center gap-2 p-2 rounded-md hover:bg-gray-800 transition-colors"
              >
                {isExpanded ? (
                  <ChevronDown className="w-4 h-4 text-gray-400" />
                ) : (
                  <ChevronRight className="w-4 h-4 text-gray-400" />
                )}
                <div
                  className="p-1.5 rounded"
                  style={{ backgroundColor: `${category.color}20` }}
                >
                  {CategoryIcon && (
                    <CategoryIcon size={14} style={{ color: category.color }} />
                  )}
                </div>
                <span className={`font-medium transition-colors ${isPM ? 'text-xs text-blue-400 uppercase tracking-widest font-black' : 'text-sm text-gray-200'}`}>
                  {category.label}
                </span>
                <span className="ml-auto text-xs text-gray-500">
                  {templates.length}
                </span>
              </button>

              {isExpanded && (
                <div className="ml-6 mt-1 space-y-1">
                  {templates.map((template) => {
                    const NodeIcon = Icons[
                      template.icon as IconName
                    ] as React.ComponentType<{
                      size?: number;
                      className?: string;
                      style?: React.CSSProperties;
                    }>;
                    const color = getCategoryColor(template.category);

                    return (
                      <div
                        key={template.id}
                        draggable
                        onDragStart={(e) => onDragStart(e, template)}
                        className={`
                          flex items-center gap-2 p-2 cursor-grab transition-all group active:cursor-grabbing border
                          ${isPM 
                            ? "rounded-xl glassmorphism border-white/5 hover:border-blue-500/30 hover:bg-blue-500/5 shadow-lg" 
                            : "rounded-md bg-gray-800 border-gray-700 hover:border-gray-500 hover:bg-gray-750"}
                        `}
                      >
                        <GripVertical className="w-3 h-3 text-gray-500 group-hover:text-gray-400" />
                        <div
                          className={`p-1.5 rounded transition-colors ${isPM ? 'shadow-inner bg-black/20' : ''}`}
                          style={{ backgroundColor: isPM ? undefined : `${color}15` }}
                        >
                          {NodeIcon && <NodeIcon size={isPM ? 16 : 14} style={{ color }} />}
                        </div>
                        <span className={`truncate ${isPM ? 'text-xs font-bold text-gray-200 tracking-tight' : 'text-sm text-gray-300'}`}>
                          {isPM ? getAnalogy(template.label) : template.label}
                        </span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="p-3 border-t border-gray-700">
        <p className="text-xs text-gray-500 text-center">
          Drag and drop nodes to the canvas
        </p>
      </div>
    </div>
  );
}
