from typing import List, Dict, Type
import logging
from uuid import UUID
from sqlmodel import Session, select
from apps.api.ingestors.aws.base import BaseDetector
from apps.api.ingestors.aws.schemas import DiscoveryResult, DiscoveryNode, DiscoveryEdge
from apps.api.models import Node, Edge, NodeType, EdgeType

logger = logging.getLogger(__name__)

class DiscoveryManager:
    def __init__(self, session: Session):
        self.session = session
        self.detectors: Dict[str, BaseDetector] = {}

    def register_detector(self, detector: BaseDetector):
        self.detectors[detector.source_name] = detector

    async def run_discovery(self, client_id: UUID, graph_id: UUID, source_names: List[str] = None, **kwargs):
        sources = source_names or self.detectors.keys()
        
        for name in sources:
            detector = self.detectors.get(name)
            if not detector:
                logger.warning(f"Detector {name} not found")
                continue
            
            try:
                result = await detector.discover(**kwargs)
                await self._merge_result(client_id, graph_id, result)
            except Exception as e:
                logger.error(f"Discovery failed for {name}: {e}")

    async def _merge_result(self, client_id: UUID, graph_id: UUID, result: DiscoveryResult):
        # 1. Identity Resolution & Node Merging
        for d_node in result.nodes:
            # Check if node exists by key
            statement = select(Node).where(
                Node.client_id == client_id,
                Node.graph_id == graph_id,
                Node.key == d_node.key
            )
            existing_node = self.session.exec(statement).first()
            
            # Find or infer NodeType ID (simplified)
            node_type_id = await self._get_node_type_id(client_id, graph_id, d_node.node_type)
            
            if existing_node:
                # Update properties if needed (merge logic)
                existing_node.properties.update(d_node.properties)
                existing_node.source = result.source
                existing_node.source_metadata.update(d_node.source_metadata)
                self.session.add(existing_node)
            else:
                new_node = Node(
                    client_id=client_id,
                    graph_id=graph_id,
                    node_type_id=node_type_id,
                    key=d_node.key,
                    display_name=d_node.display_name or d_node.key,
                    properties=d_node.properties,
                    source=result.source,
                    source_metadata=d_node.source_metadata
                )
                self.session.add(new_node)
        
        self.session.commit()

        # 2. Edge Merging
        for d_edge in result.edges:
            # Find from/to nodes
            from_node = self.session.exec(select(Node).where(Node.key == d_edge.from_node_key, Node.graph_id == graph_id)).first()
            to_node = self.session.exec(select(Node).where(Node.key == d_edge.to_node_key, Node.graph_id == graph_id)).first()
            
            if not from_node or not to_node:
                continue
            
            edge_type_id = await self._get_edge_type_id(client_id, graph_id, d_edge.edge_type)
            
            # Check if edge exists
            statement = select(Edge).where(
                Edge.from_node_id == from_node.id,
                Edge.to_node_id == to_node.id,
                Edge.edge_type_id == edge_type_id
            )
            existing_edge = self.session.exec(statement).first()
            
            if not existing_edge:
                new_edge = Edge(
                    client_id=client_id,
                    graph_id=graph_id,
                    edge_type_id=edge_type_id,
                    from_node_id=from_node.id,
                    to_node_id=to_node.id,
                    properties=d_edge.properties
                )
                self.session.add(new_edge)
        
        self.session.commit()

    async def _get_node_type_id(self, client_id, graph_id, type_name) -> UUID:
        statement = select(NodeType).where(NodeType.name == type_name, NodeType.graph_id == graph_id)
        nt = self.session.exec(statement).first()
        if not nt:
            # Fallback: create if not exists or return generic
            nt = NodeType(client_id=client_id, graph_id=graph_id, name=type_name)
            self.session.add(nt)
            self.session.commit()
            self.session.refresh(nt)
        return nt.id

    async def _get_edge_type_id(self, client_id, graph_id, type_name) -> UUID:
        statement = select(EdgeType).where(EdgeType.name == type_name, EdgeType.graph_id == graph_id)
        et = self.session.exec(statement).first()
        if not et:
            et = EdgeType(client_id=client_id, graph_id=graph_id, name=type_name)
            self.session.add(et)
            self.session.commit()
            self.session.refresh(et)
        return et.id
