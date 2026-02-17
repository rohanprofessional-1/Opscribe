import { useState, useCallback, useRef } from "react";
import ReactFlow, {
  addEdge,
  useNodesState,
  useEdgesState,
  Controls,
  Background,
  BackgroundVariant,
  MiniMap,
} from "reactflow";
import type { Node, Connection, ReactFlowInstance } from "reactflow";
import "reactflow/dist/style.css";

import NodePalette from "./NodePalette";
import PropertiesPanel from "./PropertiesPanel";
import InfrastructureNode from "./InfrastructureNode";
import type {
  NodeTemplate,
  InfrastructureNodeData,
} from "../types/infrastructure";
import { getCategoryColor } from "../data/nodeTemplates.ts";

const nodeTypes = {
  infrastructureNode: InfrastructureNode,
};

const defaultEdgeOptions = {
  style: { strokeWidth: 2, stroke: "#6b7280" },
  type: "smoothstep",
  animated: true,
};

let nodeId = 0;
const getId = () => `node_${nodeId++}`;

export default function InfrastructureDesigner() {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [reactFlowInstance, setReactFlowInstance] =
    useState<ReactFlowInstance | null>(null);
  const [selectedNode, setSelectedNode] =
    useState<Node<InfrastructureNodeData> | null>(null);

  const onConnect = useCallback(
    (params: Connection) => {
      setEdges((eds) => addEdge({ ...params, ...defaultEdgeOptions }, eds));
    },
    [setEdges],
  );

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();

      const templateData = event.dataTransfer.getData("application/reactflow");
      if (!templateData || !reactFlowInstance || !reactFlowWrapper.current) {
        return;
      }

      const template: NodeTemplate = JSON.parse(templateData);
      const bounds = reactFlowWrapper.current.getBoundingClientRect();
      const position = reactFlowInstance.screenToFlowPosition({
        x: event.clientX - bounds.left,
        y: event.clientY - bounds.top,
      });

      const newNode: Node<InfrastructureNodeData> = {
        id: getId(),
        type: "infrastructureNode",
        position,
        data: {
          label: template.label,
          category: template.category,
          icon: template.icon,
          ...template.defaultData,
        } as InfrastructureNodeData,
      };

      setNodes((nds) => nds.concat(newNode));
    },
    [reactFlowInstance, setNodes],
  );

  const onDragStart = (event: React.DragEvent, template: NodeTemplate) => {
    event.dataTransfer.setData(
      "application/reactflow",
      JSON.stringify(template),
    );
    event.dataTransfer.effectAllowed = "move";
  };

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node<InfrastructureNodeData>) => {
      setSelectedNode(node);
    },
    [],
  );

  const onPaneClick = useCallback(() => {
    setSelectedNode(null);
  }, []);

  const onUpdateNode = useCallback(
    (nodeId: string, data: Partial<InfrastructureNodeData>) => {
      setNodes((nds) =>
        nds.map((node) => {
          if (node.id === nodeId) {
            const updatedNode = {
              ...node,
              data: { ...node.data, ...data },
            };
            setSelectedNode(updatedNode as Node<InfrastructureNodeData>);
            return updatedNode;
          }
          return node;
        }),
      );
    },
    [setNodes],
  );

  const onDeleteNode = useCallback(
    (nodeId: string) => {
      setNodes((nds) => nds.filter((node) => node.id !== nodeId));
      setEdges((eds) =>
        eds.filter((edge) => edge.source !== nodeId && edge.target !== nodeId),
      );
      setSelectedNode(null);
    },
    [setNodes, setEdges],
  );

  const onCloseProperties = useCallback(() => {
    setSelectedNode(null);
  }, []);

  return (
    <div className="flex h-screen bg-gray-950">
      {/* Left Panel - Node Palette */}
      <NodePalette onDragStart={onDragStart} />

      {/* Middle - Canvas */}
      <div className="flex-1 relative" ref={reactFlowWrapper}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onInit={setReactFlowInstance}
          onDrop={onDrop}
          onDragOver={onDragOver}
          onNodeClick={onNodeClick}
          onPaneClick={onPaneClick}
          nodeTypes={nodeTypes}
          defaultEdgeOptions={defaultEdgeOptions}
          fitView
          snapToGrid
          snapGrid={[15, 15]}
          className="bg-gray-950"
        >
          <Controls className="!bg-gray-800 !border-gray-700 !rounded-lg [&>button]:!bg-gray-800 [&>button]:!border-gray-700 [&>button]:!text-gray-300 [&>button:hover]:!bg-gray-700" />
          <MiniMap
            className="!bg-gray-800 !border-gray-700 !rounded-lg"
            nodeColor={(node) =>
              getCategoryColor((node.data as InfrastructureNodeData).category)
            }
            maskColor="rgba(0, 0, 0, 0.7)"
          />
          <Background
            variant={BackgroundVariant.Dots}
            gap={20}
            size={1}
            color="#374151"
          />
        </ReactFlow>

        {/* Canvas Header */}
        <div className="absolute top-4 left-4 bg-gray-800/90 backdrop-blur-sm rounded-lg px-4 py-2 border border-gray-700">
          <h1 className="text-sm font-medium text-white">
            Infrastructure Designer
          </h1>
          <p className="text-xs text-gray-400">
            {nodes.length} nodes · {edges.length} connections
          </p>
        </div>
      </div>

      {/* Right Panel - Properties */}
      <PropertiesPanel
        selectedNode={selectedNode}
        onUpdateNode={onUpdateNode}
        onDeleteNode={onDeleteNode}
        onClose={onCloseProperties}
      />
    </div>
  );
}
