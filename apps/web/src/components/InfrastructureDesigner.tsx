/**
 * This component is the infrastructure designer for the infrastructure design
 * and will be the main component for the infrastructure design.
 * It displays the canvas, the node palette, the properties panel, and the controls.
 * It also allows the user to drag and drop nodes onto the canvas.
 * It also allows the user to select a node and edit its properties.
 * It also allows the user to delete a node.
 */

import { useState, useCallback, useRef, useEffect } from "react";
import ReactFlow, {
  addEdge,
  useNodesState,
  useEdgesState,
  Controls,
  Background,
  BackgroundVariant,
  MiniMap,
  MarkerType,
} from "reactflow";
import type { Node, Edge, Connection, ReactFlowInstance } from "reactflow";
import "reactflow/dist/style.css";
import { ArrowLeft, Bot } from "lucide-react";

import NodePalette from "./NodePalette";
import GithubConnectPanel from "./GithubConnectPanel";
import PropertiesPanel from "./PropertiesPanel";
import RAGChat from "./RAGChat";
import InfrastructureNode from "./InfrastructureNode";
import type {
  NodeTemplate,
  InfrastructureNodeData,
  InfrastructureDesign,
} from "../types/infrastructure";
import { getCategoryColor } from "../data/nodeTemplates";
import { api } from "../api/client";

const nodeTypes = {
  infrastructureNode: InfrastructureNode,
};

const defaultEdgeOptions = {
  style: { strokeWidth: 2, stroke: "#6b7280" },
  type: "smoothstep",
  animated: true,
  markerEnd: {
    type: MarkerType.ArrowClosed,
  },
};

const getId = () =>
  `node_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;

const isUuid = (s: string) =>
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(s);

interface InfrastructureDesignerProps {
  design: InfrastructureDesign | null;
  onBack: (
    nodes: Node<InfrastructureNodeData>[],
    edges: Edge[],
    name: string,
  ) => void;
}

export default function InfrastructureDesigner({
  design,
  onBack,
}: InfrastructureDesignerProps) {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const initialNodes = design?.nodes ?? [];
  const initialEdges = (design?.edges ?? []).map((e) => ({
    ...e,
    ...defaultEdgeOptions,
  }));
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [designName, setDesignName] = useState(
    design?.name ?? "Untitled Infrastructure",
  );
  const [reactFlowInstance, setReactFlowInstance] =
    useState<ReactFlowInstance | null>(null);
  const [selectedNode, setSelectedNode] =
    useState<Node<InfrastructureNodeData> | null>(null);
  const [loadingVisualization, setLoadingVisualization] = useState(false);
  const fetchedGraphIdRef = useRef<string | null>(null);

  // UI State for toggling the AI Assistant panel on the right sidebar
  const [showRagPanel, setShowRagPanel] = useState(false);

  // Stores the anonymous session ID for RAG context tracking
  const [clientId, setClientId] = useState<string>("");

  useEffect(() => {
    // Fetch the current authenticated user session to track RAG queries and metadata
    api.getCurrentUser().then((c) => setClientId(c.id)).catch(console.error);
  }, []);

  // Load nodes/edges from API when opening a graph by id (UUID) that has no nodes yet
  useEffect(() => {
    if (!design?.id || !isUuid(design.id) || design.nodes.length > 0) return;
    if (fetchedGraphIdRef.current === design.id) return;
    fetchedGraphIdRef.current = design.id;
    setLoadingVisualization(true);
    api
      .getVisualization(design.id)
      .then(({ nodes: apiNodes, edges: apiEdges }) => {
        const idToKey: Record<string, string> = {};
        apiNodes.forEach((n) => {
          idToKey[n.id] = n.key;
        });
        const pos = (p: unknown) => {
          if (p && typeof p === "object" && "x" in p && "y" in p)
            return { x: Number((p as { x: unknown }).x), y: Number((p as { y: unknown }).y) };
          return { x: 0, y: 0 };
        };
        const rfNodes = apiNodes.map((n) => ({
          id: n.key,
          type: "infrastructureNode" as const,
          position: pos(n.properties?.position),
          data: {
            label: n.display_name ?? n.key,
            ...n.properties,
          } as InfrastructureNodeData,
        }));
        const rfEdges = apiEdges
          .map((e) => {
            const source = idToKey[e.from_node_id];
            const target = idToKey[e.to_node_id];
            if (!source || !target) return null;
            return {
              id: e.id,
              source,
              target,
              ...defaultEdgeOptions,
            };
          })
          .filter((e): e is NonNullable<typeof e> => e != null);
        setNodes(rfNodes);
        setEdges(rfEdges);
      })
      .finally(() => setLoadingVisualization(false));
  }, [design?.id]);

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

  const deselectEdges = useCallback(() => {
    setEdges((eds) =>
      eds.map((e) => ({
        ...e,
        selected: false,
        style: { strokeWidth: 2, stroke: "#6b7280" },
      })),
    );
  }, [setEdges]);

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node<InfrastructureNodeData>) => {
      setSelectedNode(node);
      setShowRagPanel(false); // Hide RAG panel if we are directly clicking a node
      deselectEdges();
    },
    [deselectEdges],
  );

  const onPaneClick = useCallback(() => {
    setSelectedNode(null);
    deselectEdges();
  }, [deselectEdges]);

  const onEdgeClick = useCallback(
    (_: React.MouseEvent, edge: Edge) => {
      setSelectedNode(null);
      setEdges((eds) =>
        eds.map((e) => ({
          ...e,
          selected: e.id === edge.id,
          style:
            e.id === edge.id
              ? { strokeWidth: 3, stroke: "#ef4444" }
              : { strokeWidth: 2, stroke: "#6b7280" },
        })),
      );
    },
    [setEdges],
  );

  const onUpdateNode = useCallback(
    (nodeId: string, data: Partial<InfrastructureNodeData>) => {
      setNodes(
        (nds) =>
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
          }) as Node<InfrastructureNodeData>[],
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

  // Handle keyboard delete for selected edges
  const onKeyDown = useCallback(
    (event: React.KeyboardEvent) => {
      if (event.key === "Backspace" || event.key === "Delete") {
        setEdges((eds) => eds.filter((e) => !e.selected));
      }
    },
    [setEdges],
  );

  const handleBack = useCallback(() => {
    onBack(nodes, edges, designName);
  }, [nodes, edges, designName, onBack]);

  return (
    <div className="flex h-screen bg-gray-950">
      <NodePalette onDragStart={onDragStart} />
      <GithubConnectPanel />

      <div className="flex-1 relative" ref={reactFlowWrapper}>
        {loadingVisualization && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-gray-950/80 text-gray-400">
            Loading design...
          </div>
        )}
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
          onEdgeClick={onEdgeClick}
          onKeyDown={onKeyDown}
          nodeTypes={nodeTypes}
          defaultEdgeOptions={defaultEdgeOptions}
          deleteKeyCode={["Backspace", "Delete"]}
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

        <div className="absolute top-4 left-4 flex items-center gap-3 bg-gray-800/90 backdrop-blur-sm rounded-lg px-4 py-2 border border-gray-700">
          <button
            onClick={handleBack}
            className="p-1.5 rounded-md hover:bg-gray-700 text-gray-400 hover:text-white transition-colors"
            title="Back to designs"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <input
              type="text"
              value={designName}
              onChange={(e) => setDesignName(e.target.value)}
              className="bg-transparent text-sm font-medium text-white focus:outline-none focus:ring-0 border-none p-0 min-w-[120px]"
            />
            <p className="text-xs text-gray-400">
              {nodes.length} nodes · {edges.length} connections
            </p>
          </div>
        </div>
        <div className="absolute top-4 right-4 z-10">
          <button
            onClick={() => setShowRagPanel(!showRagPanel)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition-colors shadow-lg ${showRagPanel
              ? "bg-blue-600 border-blue-500 text-white"
              : "bg-gray-800 border-gray-700 text-gray-300 hover:bg-gray-700 hover:text-white"
              }`}
          >
            <Bot className={`w-4 h-4 ${showRagPanel ? "text-white" : "text-blue-400"}`} />
            <span className="text-sm font-medium">AI Assistant</span>
          </button>
        </div>
      </div>

      {/* 
          Right Side Sidebar 
          Dynamically switches between the selected node properties and the AI Assistant chat.
      */}
      {showRagPanel ? (
        <RAGChat
          clientId={clientId}
          graphId={design?.id || ""}
          nodes={nodes}
          edges={edges}
          designName={designName}
          onClose={() => setShowRagPanel(false)}
        />
      ) : (
        <PropertiesPanel
          selectedNode={selectedNode}
          onUpdateNode={onUpdateNode}
          onDeleteNode={onDeleteNode}
          onClose={onCloseProperties}
        />
      )}
    </div>
  );
}
