"""
Graph reasoning engine for cognitive diagram navigation.

Implements navigation, pattern matching, rewriting, and reasoning
over directed acyclic graphs representing logical/mathematical structures.
"""

import structlog
from typing import Any, Optional
from collections import deque
import networkx as nx

from .models import Diagram, DiagramNode, DiagramEdge, Pattern


logger = structlog.get_logger(__name__)


class NavigationMemory:
    """Tracks position and exploration state during navigation."""

    def __init__(self, position: str) -> None:
        self.position = position
        self.context_window: list[DiagramNode] = []
        self.visited_trajectory: list[str] = []
        self.distance_estimates: dict[str, float] = {}
        self.exploration_count: dict[str, int] = {}
        self.confidence: float = 0.0


class GraphEngine:
    """
    Core engine for diagrammatic reasoning.

    Manages diagram storage, navigation, pattern matching, and rule application.
    Thread-safe for MCP server use.
    """

    def __init__(self, max_diagrams: int = 1000) -> None:
        """
        Initialize the reasoning engine.

        Args:
            max_diagrams: Maximum number of diagrams to keep in memory
        """
        self.diagrams: dict[str, Diagram] = {}
        self.max_diagrams = max_diagrams
        self.graph_cache: dict[str, nx.DiGraph] = {}
        self.logger = structlog.get_logger(__name__)

    def create_diagram(
        self,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
    ) -> str:
        """
        Create a new diagram from specification.

        Args:
            nodes: List of node dicts with 'id', 'label', 'type'
            edges: List of edge dicts with 'source', 'target', 'label'

        Returns:
            str: The diagram ID

        Raises:
            ValueError: If specification is invalid
        """
        diagram = Diagram.create(nodes, edges)

        if not diagram.is_valid():
            raise ValueError("Invalid diagram specification")

        self.diagrams[diagram.diagram_id] = diagram
        self._build_networkx_graph(diagram)

        self.logger.info(f"Created diagram {diagram.diagram_id} with {diagram.num_nodes()} nodes")
        return diagram.diagram_id

    def get_diagram(self, diagram_id: str) -> Optional[Diagram]:
        """Retrieve a diagram by ID."""
        return self.diagrams.get(diagram_id)

    def _build_networkx_graph(self, diagram: Diagram) -> nx.DiGraph:
        """Build NetworkX representation for algorithms."""
        g = nx.DiGraph()

        # Add nodes with attributes
        for node_id, node in diagram.nodes.items():
            g.add_node(node_id, label=node.label, type=node.node_type)

        # Add edges
        for edge in diagram.edges:
            g.add_edge(edge.source, edge.target, label=edge.label, weight=edge.weight)

        self.graph_cache[diagram.diagram_id] = g
        return g

    def navigate_breadth_first(
        self,
        diagram_id: str,
        start_node: str,
        max_depth: int = 5,
    ) -> dict[str, Any]:
        """
        Explore diagram using breadth-first traversal.

        Args:
            diagram_id: ID of diagram to navigate
            start_node: Starting node ID
            max_depth: Maximum exploration depth

        Returns:
            dict with explored_nodes, edges_traversed, exploration_path
        """
        diagram = self.get_diagram(diagram_id)
        if not diagram:
            raise ValueError(f"Diagram {diagram_id} not found")

        if start_node not in diagram.nodes:
            raise ValueError(f"Node {start_node} not found in diagram")

        explored_nodes = []
        edges_traversed = []
        queue: deque[tuple[str, int]] = deque([(start_node, 0)])
        visited = {start_node}

        while queue:
            node_id, depth = queue.popleft()
            if depth > max_depth:
                break

            node = diagram.nodes[node_id]
            explored_nodes.append({
                'id': node_id,
                'label': node.label,
                'depth': depth,
                'type': node.node_type,
            })

            # Explore outgoing edges
            for edge in diagram.get_outgoing_edges(node_id):
                edges_traversed.append({
                    'from': edge.source,
                    'to': edge.target,
                    'label': edge.label,
                })

                if edge.target not in visited:
                    visited.add(edge.target)
                    queue.append((edge.target, depth + 1))

        return {
            'explored_nodes': explored_nodes,
            'edges_traversed': edges_traversed,
            'total_explored': len(explored_nodes),
        }

    def navigate_guided(
        self,
        diagram_id: str,
        start_node: str,
        goal_node: str,
        heuristic: str = 'distance',
    ) -> dict[str, Any]:
        """
        Navigate from start to goal using guided search.

        Args:
            diagram_id: ID of diagram
            start_node: Starting node
            goal_node: Target node
            heuristic: 'distance' or 'reward'

        Returns:
            dict with path, cost, explanation
        """
        diagram = self.get_diagram(diagram_id)
        if not diagram:
            raise ValueError(f"Diagram {diagram_id} not found")

        if start_node not in diagram.nodes or goal_node not in diagram.nodes:
            raise ValueError("Start or goal node not found")

        g = self.graph_cache.get(diagram_id)
        if not g:
            g = self._build_networkx_graph(diagram)

        try:
            # Use Dijkstra's algorithm for shortest path
            path = nx.shortest_path(g, start_node, goal_node, weight='weight')
            cost = nx.shortest_path_length(g, start_node, goal_node, weight='weight')

            return {
                'found': True,
                'path': path,
                'cost': cost,
                'num_steps': len(path) - 1,
                'heuristic_used': heuristic,
            }
        except nx.NetworkXNoPath:
            return {
                'found': False,
                'path': [],
                'cost': float('inf'),
                'num_steps': -1,
                'reason': 'No path exists between nodes',
            }

    def analyze_reachability(
        self,
        diagram_id: str,
        source: str,
        targets: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """
        Analyze what nodes are reachable from a source.

        Args:
            diagram_id: ID of diagram
            source: Source node
            targets: Optional target nodes to check

        Returns:
            dict with reachable_nodes, distance_map, bottleneck_nodes
        """
        diagram = self.get_diagram(diagram_id)
        if not diagram:
            raise ValueError(f"Diagram {diagram_id} not found")

        g = self.graph_cache.get(diagram_id)
        if not g:
            g = self._build_networkx_graph(diagram)

        # Compute shortest paths
        distances = nx.single_source_dijkstra_path_length(g, source, weight='weight')

        reachable = {
            'source': source,
            'total_reachable': len(distances),
            'nodes': [
                {
                    'id': node_id,
                    'distance': int(dist),
                    'label': diagram.nodes[node_id].label,
                }
                for node_id, dist in sorted(distances.items(), key=lambda x: x[1])
            ],
        }

        # Check specific targets if provided
        if targets:
            target_reachability = {
                target: target in distances
                for target in targets
            }
            reachable['target_reachability'] = target_reachability

        return reachable

    def pattern_match(
        self,
        diagram_id: str,
        pattern: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Find all matches of a pattern within a diagram.

        Args:
            diagram_id: ID of diagram to search
            pattern: Pattern specification with 'nodes' and 'edges'

        Returns:
            dict with matches (list of node mappings)
        """
        diagram = self.get_diagram(diagram_id)
        if not diagram:
            raise ValueError(f"Diagram {diagram_id} not found")

        # Simple pattern matching - look for isomorphic subgraphs
        matches = []
        pattern_nodes = pattern.get('nodes', {})
        pattern_edges = pattern.get('edges', [])

        # Try each node as potential start
        for potential_root in diagram.nodes:
            mapping = self._try_match_from_node(
                diagram, potential_root, pattern_nodes, pattern_edges
            )
            if mapping:
                matches.append(mapping)

        return {
            'pattern': pattern,
            'matches': matches,
            'num_matches': len(matches),
        }

    def _try_match_from_node(
        self,
        diagram: Diagram,
        start_node: str,
        pattern_nodes: dict[str, Any],
        pattern_edges: list[tuple[str, str, dict[str, Any]]],
    ) -> Optional[dict[str, str]]:
        """
        Try to match pattern starting from a specific node using backtracking.
        """
        if not pattern_nodes:
            return None

        # Sort pattern nodes to have a deterministic order
        p_node_ids = sorted(pattern_nodes.keys())
        first_p_node = p_node_ids[0]

        def backtrack(p_idx: int, current_mapping: dict[str, str], used_d_nodes: set[str]) -> Optional[dict[str, str]]:
            if p_idx == len(p_node_ids):
                # Verify all edges in pattern are satisfied by the mapping
                for p_src, p_tgt, _ in pattern_edges:
                    d_src = current_mapping[p_src]
                    d_tgt = current_mapping[p_tgt]
                    # Check if edge exists in diagram
                    if not any(e.target == d_tgt for e in diagram.get_outgoing_edges(d_src)):
                        return None
                return current_mapping

            p_node_id = p_node_ids[p_idx]

            # If this is the first node, it must be the start_node (provided by caller)
            if p_idx == 0:
                # Check constraints for start_node
                if self._check_node_constraints(diagram.nodes[start_node], pattern_nodes[p_node_id]):
                    current_mapping[p_node_id] = start_node
                    return backtrack(p_idx + 1, current_mapping, used_d_nodes | {start_node})
                return None

            # Try mapping p_node_id to any unused diagram node that satisfies constraints
            for d_node_id, d_node in diagram.nodes.items():
                if d_node_id in used_d_nodes:
                    continue

                if self._check_node_constraints(d_node, pattern_nodes[p_node_id]):
                    current_mapping[p_node_id] = d_node_id
                    result = backtrack(p_idx + 1, current_mapping, used_d_nodes | {d_node_id})
                    if result:
                        return result
                    del current_mapping[p_node_id]

            return None

        return backtrack(0, {}, set())

    def _check_node_constraints(self, node: DiagramNode, constraints: dict[str, Any]) -> bool:
        """Check if a node satisfies pattern constraints."""
        if 'type' in constraints and node.node_type != constraints['type']:
            return False
        if 'label' in constraints and node.label != constraints['label']:
            return False
        # Add more constraint checks as needed
        return True

    def compute_metrics(
        self,
        diagram_id: str,
        metrics: list[str],
    ) -> dict[str, Any]:
        """
        Compute structural metrics on a diagram.

        Args:
            diagram_id: ID of diagram
            metrics: List of metric names to compute

        Returns:
            dict with requested metrics
        """
        diagram = self.get_diagram(diagram_id)
        if not diagram:
            raise ValueError(f"Diagram {diagram_id} not found")

        g = self.graph_cache.get(diagram_id)
        if not g:
            g = self._build_networkx_graph(diagram)

        results: dict[str, Any] = {}

        for metric in metrics:
            if metric == 'chain_length':
                # Longest path in DAG
                if nx.is_directed_acyclic_graph(g):
                    try:
                        nodes_list = list(g.nodes())
                        if len(nodes_list) >= 2:
                            lengths = []
                            for path in nx.all_simple_paths(g, nodes_list[0], nodes_list[-1]):
                                lengths.append(len(path) - 1)
                            results['chain_length'] = max(lengths) if lengths else 0
                        else:
                            results['chain_length'] = 0
                    except (nx.NetworkXNoPath, nx.NodeNotFound):
                        results['chain_length'] = 0
                else:
                    results['chain_length'] = None

            elif metric == 'branching_factor':
                # Average out-degree
                if g.nodes():
                    out_degrees = [g.out_degree(n) for n in g.nodes()]
                    results['branching_factor'] = sum(out_degrees) / len(out_degrees)
                else:
                    results['branching_factor'] = 0.0

            elif metric == 'density':
                # Graph density
                results['density'] = nx.density(g)

            elif metric == 'num_nodes':
                results['num_nodes'] = g.number_of_nodes()

            elif metric == 'num_edges':
                results['num_edges'] = g.number_of_edges()

            elif metric == 'is_dag':
                results['is_dag'] = nx.is_directed_acyclic_graph(g)

        return results
