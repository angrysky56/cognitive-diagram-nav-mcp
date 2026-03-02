"""
Core data structures for cognitive diagram navigation.

Implements graph representation, patterns, and navigation memory
following Quantomatic's diagrammatic reasoning principles.
"""

from dataclasses import dataclass, field
from typing import Any, Optional
from datetime import datetime
import uuid


@dataclass
class DiagramNode:
    """
    Represents a node in a diagram.

    Maps to operations, terminals, or control flow elements in the reasoning space.
    Supports embedding vectors for similarity-based navigation.
    """

    id: str
    label: str
    node_type: str  # 'operation', 'terminal', 'control', 'composite'
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: Optional[list[float]] = None
    visited: bool = False
    depth: int = 0

    def __post_init__(self) -> None:
        """Validate node on creation."""
        valid_types = {'operation', 'terminal', 'control', 'composite'}
        if self.node_type not in valid_types:
            raise ValueError(f"node_type must be one of {valid_types}")


@dataclass
class DiagramEdge:
    """
    Represents a directed edge in a diagram.

    Connects nodes with labeled relationships and associated properties.
    Supports weighted edges for cost-based navigation.
    """

    source: str  # node_id
    target: str  # node_id
    label: str
    properties: dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0

    def __post_init__(self) -> None:
        """Validate edge on creation."""
        if self.weight <= 0:
            raise ValueError("edge weight must be positive")


@dataclass
class Pattern:
    """
    Represents a pattern for matching within diagrams.

    Supports variable-arity operations through !-boxes (like in Quantomatic).
    Used for graph rewriting and structural matching.
    """

    nodes: dict[str, dict[str, Any]]  # node_pattern_id -> {type, constraints}
    edges: list[tuple[str, str, dict[str, Any]]]  # (src, tgt, constraints)
    variable_arity_boxes: list[str] = field(default_factory=list)

    def validate(self) -> bool:
        """Check well-formedness conditions for patterns."""
        if not self.nodes or not self.edges:
            return False

        # Verify all edge endpoints reference existing nodes
        node_ids = set(self.nodes.keys())
        for src, tgt, _ in self.edges:
            if src not in node_ids or tgt not in node_ids:
                return False

        return True


@dataclass
class Diagram:
    """
    Complete representation of a reasoning diagram.

    Contains graph structure, metadata, and provenance information.
    Primary unit of reasoning in the cognitive navigation system.
    """

    diagram_id: str
    nodes: dict[str, DiagramNode] = field(default_factory=dict)
    edges: list[DiagramEdge] = field(default_factory=list)
    root_node: Optional[str] = None
    invariants: list[str] = field(default_factory=list)  # proven properties
    transformations: list[str] = field(default_factory=list)  # rule application history
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    metadata: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def create(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> 'Diagram':
        """
        Factory method to create a new diagram from node/edge specifications.

        Args:
            nodes: List of node specifications with 'id', 'label', 'type', optional 'metadata'
            edges: List of edge specifications with 'source', 'target', 'label', optional 'weight'

        Returns:
            Diagram: Initialized diagram ready for reasoning
        """
        diagram_id = str(uuid.uuid4())
        diagram = Diagram(diagram_id=diagram_id)

        # Add nodes
        for node_spec in nodes:
            node = DiagramNode(
                id=node_spec['id'],
                label=node_spec['label'],
                node_type=node_spec.get('type', 'operation'),
                metadata=node_spec.get('metadata', {}),
                embedding=node_spec.get('embedding'),
            )
            diagram.nodes[node.id] = node

        # Add edges
        for edge_spec in edges:
            edge = DiagramEdge(
                source=edge_spec['source'],
                target=edge_spec['target'],
                label=edge_spec['label'],
                properties=edge_spec.get('properties', {}),
                weight=edge_spec.get('weight', 1.0),
            )
            diagram.edges.append(edge)

        # Set root if not provided
        if diagram.nodes:
            diagram.root_node = nodes[0]['id']

        return diagram

    def get_node(self, node_id: str) -> Optional[DiagramNode]:
        """Retrieve a node by ID."""
        return self.nodes.get(node_id)

    def get_outgoing_edges(self, node_id: str) -> list[DiagramEdge]:
        """Get all edges departing from a node."""
        return [e for e in self.edges if e.source == node_id]

    def get_incoming_edges(self, node_id: str) -> list[DiagramEdge]:
        """Get all edges arriving at a node."""
        return [e for e in self.edges if e.target == node_id]

    def num_nodes(self) -> int:
        """Return node count."""
        return len(self.nodes)

    def num_edges(self) -> int:
        """Return edge count."""
        return len(self.edges)

    def is_valid(self) -> bool:
        """
        Verify diagram well-formedness.

        Checks:
        - All edge endpoints reference existing nodes
        - Root node exists if specified
        """
        node_ids = set(self.nodes.keys())

        for edge in self.edges:
            if edge.source not in node_ids or edge.target not in node_ids:
                return False

        if self.root_node and self.root_node not in node_ids:
            return False

        return True
