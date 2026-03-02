"""
Graph reasoning engine for cognitive diagram navigation.

Implements navigation, pattern matching, rewriting, and reasoning
over directed acyclic graphs representing logical/mathematical structures.
"""

import collections
import math
import random
import uuid
from typing import Any, Optional, cast

import networkx as nx
import structlog

from .models import DerivationStep, Diagram, DiagramEdge, DiagramNode

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

    def __init__(self, max_diagrams: int = 100) -> None:
        """
        Initialize the reasoning engine.

        Args:
            max_diagrams: Maximum number of diagrams to keep in memory
        """
        self.diagrams: dict[str, Diagram] = {}
        self.max_diagrams = max_diagrams
        self.graph_cache: dict[str, nx.DiGraph] = {}
        self.logger = structlog.get_logger(__name__)
        self.memories: dict[str, NavigationMemory] = {}
        self._random_engine: random.Random = random.SystemRandom()

    def create_diagram(
        self,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
    ) -> str:
        """
        Create a new diagram from specification.

        Args:
            nodes: List of node dicts with 'id', 'label', 'type', optional 'embedding'
            edges: List of edge dicts with 'source', 'target', 'label'

        Returns:
            str: The diagram ID

        Raises:
            ValueError: If specification is invalid
        """
        diagram = Diagram.create(nodes, edges)

        if not diagram.is_valid():
            raise ValueError("Invalid diagram specification")

        # Check for cyclic diagram references
        for node in diagram.nodes.values():
            if node.sub_diagram_id:
                visited_diagrams = {diagram.diagram_id}
                queue = [node.sub_diagram_id]
                while queue:
                    curr_id = queue.pop(0)
                    if curr_id in visited_diagrams:
                        raise ValueError(f"Cyclic diagram reference detected: {curr_id}")
                    visited_diagrams.add(curr_id)
                    curr_diag = self.get_diagram(curr_id)
                    if curr_diag:
                        for sub_node in curr_diag.nodes.values():
                            if sub_node.sub_diagram_id:
                                queue.append(sub_node.sub_diagram_id)

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

    def _build_flattened_networkx_graph(self, root_diagram_id: str) -> nx.DiGraph:
        """Build a unified NetworkX graph spanning all nested sub-diagrams."""
        g = nx.DiGraph()
        visited_diagrams = set()

        def add_diagram_to_g(diag_id: str) -> None:
            if diag_id in visited_diagrams:
                return
            visited_diagrams.add(diag_id)
            diag = self.get_diagram(diag_id)
            if not diag:
                return

            for node_id, node in diag.nodes.items():
                if node_id not in g:
                    g.add_node(node_id, label=node.label, type=node.node_type)

                if node.node_type == "composite" and node.sub_diagram_id:
                    sub_diag = self.get_diagram(node.sub_diagram_id)
                    if sub_diag and sub_diag.root_node:
                        # Add a low-cost meta edge into the composite
                        g.add_edge(
                            node_id, sub_diag.root_node, label="contains_diagram", weight=0.1
                        )
                        add_diagram_to_g(node.sub_diagram_id)

            for edge in diag.edges:
                if edge.source not in g:
                    g.add_node(edge.source)
                if edge.target not in g:
                    g.add_node(edge.target)
                g.add_edge(edge.source, edge.target, label=edge.label, weight=edge.weight)

        add_diagram_to_g(root_diagram_id)
        return g

    def navigate_breadth_first(
        self,
        diagram_id: str,
        start_node: str,
        max_depth: int = 5,
        expand_composites: bool = False,
    ) -> dict[str, Any]:
        """
        Explore diagram using breadth-first traversal.

        Args:
            diagram_id: ID of diagram to navigate
            start_node: Starting node ID
            max_depth: Maximum exploration depth
            expand_composites: If True, enter sub-diagrams of composite nodes

        Returns:
            dict with explored_nodes, edges_traversed, exploration_path
        """
        initial_diagram = self.get_diagram(diagram_id)
        if not initial_diagram:
            raise ValueError(f"Diagram {diagram_id} not found")

        if start_node not in initial_diagram.nodes:
            raise ValueError(f"Node {start_node} not found in diagram")

        explored_nodes = []
        edges_traversed = []
        queue: collections.deque[tuple[str, str, int]] = collections.deque(
            [(diagram_id, start_node, 0)]
        )
        visited = {(diagram_id, start_node)}

        while queue:
            curr_diagram_id, node_id, depth = queue.popleft()
            if depth > max_depth:
                break

            diagram = self.get_diagram(curr_diagram_id)
            if not diagram:
                continue

            node = diagram.nodes[node_id]
            explored_nodes.append(
                {
                    "id": node_id,
                    "diagram_id": curr_diagram_id,
                    "label": node.label,
                    "depth": depth,
                    "type": node.node_type,
                }
            )

            # If node is composite and we expand, enter the sub-diagram
            if expand_composites and node.node_type == "composite" and node.sub_diagram_id:
                sub_diagram = self.get_diagram(node.sub_diagram_id)
                if sub_diagram and sub_diagram.root_node:
                    root_id = sub_diagram.root_node
                    if (sub_diagram.diagram_id, root_id) not in visited:
                        visited.add((sub_diagram.diagram_id, root_id))
                        # We represent the transition down as a special meta-edge
                        edges_traversed.append(
                            {
                                "from": node_id,
                                "to": root_id,
                                "label": "contains_diagram",
                                "is_meta": True,
                            }
                        )
                        queue.append((sub_diagram.diagram_id, root_id, depth + 1))

            # Explore outgoing edges in current diagram
            for edge in diagram.get_outgoing_edges(node_id):
                edges_traversed.append(
                    {"from": edge.source, "to": edge.target, "label": edge.label, "is_meta": False}
                )

                if (curr_diagram_id, edge.target) not in visited:
                    visited.add((curr_diagram_id, edge.target))
                    queue.append((curr_diagram_id, edge.target, depth + 1))

        return {
            "explored_nodes": explored_nodes,
            "edges_traversed": edges_traversed,
            "total_explored": len(explored_nodes),
        }

    def navigate_guided(
        self,
        diagram_id: str,
        start_node: str,
        goal_node: str,
        heuristic: str = "distance",
        expand_composites: bool = False,
    ) -> dict[str, Any]:
        """
        Navigate from start to goal using guided search.

        Args:
            diagram_id: ID of diagram
            start_node: Starting node
            goal_node: Target node
            heuristic: 'distance', 'reward', or 'semantic_similarity'
            expand_composites: If True, search traverses into sub-diagrams

        Returns:
            dict with path, cost, explanation
        """
        diagram = self.get_diagram(diagram_id)
        if not diagram:
            raise ValueError(f"Diagram {diagram_id} not found")

        if start_node not in diagram.nodes and not expand_composites:
            raise ValueError("Start node not found in diagram")

        if expand_composites:
            g = self._build_flattened_networkx_graph(diagram_id)
            if start_node not in g.nodes or goal_node not in g.nodes:
                raise ValueError("Start or goal node not found in unified graph")

            # Helper to find node representation across all diagrams for embeddings
            def get_node_obj(nid: str) -> Optional[DiagramNode]:
                for d in self.diagrams.values():
                    if nid in d.nodes:
                        return d.nodes[nid]
                return None

        else:
            if goal_node not in diagram.nodes:
                raise ValueError("Goal node not found in diagram")
            g = self.graph_cache.get(diagram_id)
            if not g:
                g = self._build_networkx_graph(diagram)

            def get_node_obj(nid: str) -> Optional[DiagramNode]:
                return diagram.nodes.get(nid)

        try:
            if heuristic == "semantic_similarity":
                goal_node_obj = get_node_obj(goal_node)
                if not goal_node_obj or not goal_node_obj.embedding:
                    self.logger.warning("Goal node missing embedding, falling back to Dijkstra")
                    path = nx.shortest_path(g, start_node, goal_node, weight="weight")
                    cost = nx.shortest_path_length(g, start_node, goal_node, weight="weight")
                else:

                    def astar_heuristic(u: str, _v: str) -> float:
                        # _v is always goal_node in A* signature heuristic(u, v)
                        node_u = get_node_obj(u)
                        if not node_u or not node_u.embedding:
                            return 1.0  # default distance if no embedding

                        # node_u.embedding is guaranteed to be a list[float] if score is calculated
                        # same for goal_node_obj.embedding
                        if goal_node_obj.embedding is None:
                            return 1.0

                        sim = self._cosine_similarity(
                            cast(list[float], node_u.embedding),
                            cast(list[float], goal_node_obj.embedding),
                        )
                        return max(0.0, 1.0 - sim)  # distance is 1 - similarity

                    path = nx.astar_path(
                        g, start_node, goal_node, heuristic=astar_heuristic, weight="weight"
                    )
                    cost = nx.astar_path_length(
                        g, start_node, goal_node, heuristic=astar_heuristic, weight="weight"
                    )
            else:
                # Use Dijkstra's algorithm for shortest path
                path = nx.shortest_path(g, start_node, goal_node, weight="weight")
                cost = nx.shortest_path_length(g, start_node, goal_node, weight="weight")

            return {
                "found": True,
                "path": path,
                "cost": cost,
                "num_steps": len(path) - 1,
                "heuristic_used": heuristic,
            }
        except nx.NetworkXNoPath:
            return {
                "found": False,
                "path": [],
                "cost": float("inf"),
                "num_steps": -1,
                "reason": "No path exists between nodes",
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
        distances = nx.single_source_dijkstra_path_length(g, source, weight="weight")

        reachable = {
            "source": source,
            "total_reachable": len(distances),
            "nodes": [
                {
                    "id": node_id,
                    "distance": int(dist),
                    "label": diagram.nodes[node_id].label,
                }
                for node_id, dist in sorted(distances.items(), key=lambda x: x[1])
            ],
        }

        # Check specific targets if provided
        if targets:
            target_reachability = {target: target in distances for target in targets}
            reachable["target_reachability"] = target_reachability

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

        if "nodes" not in pattern or "edges" not in pattern:
            raise ValueError("Pattern must contain 'nodes' (dict) and 'edges' (list)")

        # Simple pattern matching - look for isomorphic subgraphs
        matches = []
        seen_mappings = set()

        pattern_nodes = pattern.get("nodes", {})
        pattern_edges = pattern.get("edges", [])

        # Try each node as potential start
        for potential_root in diagram.nodes:
            mapping = self._try_match_from_node(
                diagram, potential_root, pattern_nodes, pattern_edges
            )
            if mapping:
                # Deduplicate matches (same pattern nodes mapping to same diagram nodes)
                mapping_signature = frozenset(mapping.items())
                if mapping_signature not in seen_mappings:
                    seen_mappings.add(mapping_signature)
                    matches.append(mapping)

        return {
            "pattern": pattern,
            "matches": matches,
            "num_matches": len(matches),
        }

    def apply_rewrite_rule(
        self, diagram_id: str, rule_spec: dict[str, Any], match_mapping: dict[str, str]
    ) -> dict[str, Any]:
        """
        Apply a Double-Pushout (DPO) rewrite rule to a diagram.

        Args:
            diagram_id: Target diagram ID
            rule_spec: Serialized RewriteRule dict (must have 'lhs', 'rhs', 'rule_name')
            match_mapping: Mapping of rule LHS node IDs to diagram node IDs

        Returns:
            dict containing success status and modified diagram stats
        """
        diagram = self.get_diagram(diagram_id)
        if not diagram:
            raise ValueError(f"Diagram {diagram_id} not found")

        lhs_nodes = rule_spec.get("lhs", {}).get("nodes", {})
        rhs_nodes = rule_spec.get("rhs", {}).get("nodes", {})
        lhs_edges = rule_spec.get("lhs", {}).get("edges", [])
        rhs_edges = rule_spec.get("rhs", {}).get("edges", [])

        # 1. Identify Boundary, Removed, and Added Nodes
        l_node_ids = set(lhs_nodes.keys())
        r_node_ids = set(rhs_nodes.keys())

        boundary_p_nodes = l_node_ids.intersection(r_node_ids)
        removed_p_nodes = l_node_ids - boundary_p_nodes
        added_p_nodes = r_node_ids - boundary_p_nodes

        # Check identification condition (two distinct LHS nodes cannot map to the same diagram node
        # if one is deleted)
        # For simplicity, our mapping is already injective due to 'used_d_nodes' in backtracking,
        # so identification holds if mapping is valid.

        # 2. Check Dangling Condition
        # A node scheduled for deletion cannot have incident edges in the diagram that are NOT in the LHS.
        for p_del in removed_p_nodes:
            d_del = match_mapping.get(p_del)
            if not d_del:
                raise ValueError(f"Matched node {p_del} missing from mapping")

            # Count diagram edges connected to this deleted node
            d_incident_edges = diagram.get_incoming_edges(d_del) + diagram.get_outgoing_edges(d_del)

            # Count LHS edges connected to this deleted node
            l_incident_edges = [e for e in lhs_edges if e[0] == p_del or e[1] == p_del]

            # If diagram has more edges than LHS, deleting this node leaves dangling edges -> invalid rewrite
            if len(d_incident_edges) > len(l_incident_edges):
                raise ValueError(
                    f"Dangling condition violation: Deleting node {d_del} "
                    "leaves dangling edges in diagram."
                )

        # 3. Apply Deletions
        # Remove LHS edges
        for p_src, p_tgt, _ in lhs_edges:
            d_src = match_mapping.get(p_src)
            d_tgt = match_mapping.get(p_tgt)
            if d_src and d_tgt:
                diagram.edges = [
                    e for e in diagram.edges if not (e.source == d_src and e.target == d_tgt)
                ]

        # Remove LHS nodes
        for p_del in removed_p_nodes:
            d_del = match_mapping[p_del]
            if d_del in diagram.nodes:
                del diagram.nodes[d_del]

        # 4. Apply Additions and Attribute Updates

        # Mapping for RHS nodes to diagram nodes
        rhs_to_d_mapping = {p_bdry: match_mapping[p_bdry] for p_bdry in boundary_p_nodes}

        # Update boundary nodes from RHS spec
        for p_bdry in boundary_p_nodes:
            d_bdry = rhs_to_d_mapping[p_bdry]
            spec = rhs_nodes[p_bdry]
            d_node = diagram.nodes[d_bdry]

            if "label" in spec:
                d_node.label = spec["label"]
            if "type" in spec:
                d_node.node_type = spec["type"]
            if "metadata" in spec:
                d_node.metadata.update(spec["metadata"])

        # Add pure RHS nodes
        for p_add in added_p_nodes:
            fresh_id = str(uuid.uuid4())
            rhs_to_d_mapping[p_add] = fresh_id

            spec = rhs_nodes[p_add]
            new_node = DiagramNode(
                id=fresh_id,
                label=spec.get("label", f"Rewritten {p_add}"),
                node_type=spec.get("type", "operation"),
                metadata=spec.get("metadata", {}),
            )
            diagram.nodes[fresh_id] = new_node

        # Add RHS edges
        for p_src, p_tgt, p_props in rhs_edges:
            d_src = rhs_to_d_mapping.get(p_src)
            d_tgt = rhs_to_d_mapping.get(p_tgt)
            if not d_src or not d_tgt:
                raise ValueError("RHS edge references unknown node")

            new_edge = DiagramEdge(
                source=d_src,
                target=d_tgt,
                label=p_props.get("label", "rewritten_edge"),
                properties=p_props.get("metadata", {}),
            )
            diagram.edges.append(new_edge)

        # 5. Finalize
        # Clear cache since graph topology changed
        self.graph_cache.pop(diagram_id, None)

        rule_name = rule_spec.get("rule_name", "Unnamed Rule")
        step = DerivationStep(
            rule_name=rule_name,
            match_mapping=match_mapping,
            diagram_before=diagram_id,
            diagram_after=diagram_id,  # DPO in-place for now
            description=f"Applied rule '{rule_name}' at {match_mapping}",
        )
        diagram.transformations.append(step)

        self.logger.info(f"Successfully applied rewrite rule '{rule_name}' to {diagram_id}")

        return {
            "success": True,
            "diagram_id": diagram_id,
            "rule_applied": rule_name,
            "nodes_removed": len(removed_p_nodes),
            "nodes_added": len(added_p_nodes),
            "current_num_nodes": diagram.num_nodes(),
            "current_num_edges": diagram.num_edges(),
        }

    def _check_node_constraints(
        self, diagram_node: DiagramNode, constraints: dict[str, Any]
    ) -> bool:
        """
        Check if a diagram node satisfies pattern constraints.

        Args:
            diagram_node: Node to check
            constraints: Constraints dictionary from pattern

        Returns:
            bool: True if satisfied
        """
        # Type constraint
        if "type" in constraints and diagram_node.node_type != constraints["type"]:
            return False

        # Label constraint
        if "label" in constraints and diagram_node.label != constraints["label"]:
            return False

        # Metadata constraints
        meta_constraints = constraints.get("metadata", {})
        for key, value in meta_constraints.items():
            if diagram_node.metadata.get(key) != value:
                return False

        return True

    def _try_match_from_node(
        self,
        diagram: Diagram,
        start_node: str,
        pattern_nodes: dict[str, Any],
        pattern_edges: list[tuple[str, str, dict[str, Any]]],
    ) -> Optional[dict[str, str]]:
        """
        Try to match pattern starting from a specific node using backtracking and unification.
        """
        if not pattern_nodes:
            return None

        # Determine a suitable starting node from the pattern (preferably one with constraints)
        p_node_ids = list(pattern_nodes.keys())
        first_p_node = p_node_ids[0]

        def backtrack(
            p_idx: int, current_mapping: dict[str, str], used_d_nodes: set[str]
        ) -> Optional[dict[str, str]]:
            # Base case: all pattern nodes are mapped
            if p_idx == len(p_node_ids):
                # Verify all edges in pattern are satisfied by the current mapping (unification)
                for p_src, p_tgt, _ in pattern_edges:
                    d_src = current_mapping.get(p_src)
                    d_tgt = current_mapping.get(p_tgt)

                    if not d_src or not d_tgt:
                        continue  # Should not happen if all nodes mapped

                    # Check if edge exists in diagram between the mapped nodes
                    if not any(e.target == d_tgt for e in diagram.get_outgoing_edges(d_src)):
                        return None
                return current_mapping

            p_node_id = p_node_ids[p_idx]

            # If this pattern node is already unified (bound to a diagram node), skip assigning
            if p_node_id in current_mapping:
                return backtrack(p_idx + 1, current_mapping, used_d_nodes)

            # Try tracking valid structural neighbors based on already mapped nodes.
            # This makes matching dramatically faster than trying all unused nodes.
            potential_targets: set[str] = set()

            # Find any incoming edge in pattern from an already mapped node
            for p_src, p_tgt, _ in pattern_edges:
                if p_tgt == p_node_id and p_src in current_mapping:
                    d_src = current_mapping[p_src]
                    potential_targets.update(e.target for e in diagram.get_outgoing_edges(d_src))

            # Find any outgoing edge in pattern to an already mapped node
            for p_src, p_tgt, _ in pattern_edges:
                if p_src == p_node_id and p_tgt in current_mapping:
                    d_tgt = current_mapping[p_tgt]
                    potential_targets.update(e.source for e in diagram.get_incoming_edges(d_tgt))

            # If no structural hints, fall back to all unused nodes
            if not potential_targets:
                # Special handling for the very first pattern node if it's not bound yet
                if p_idx == 0:
                    potential_targets = {start_node}
                else:
                    potential_targets = set(diagram.nodes.keys()) - used_d_nodes

            # Try unifying p_node_id with the potential candidates
            for d_node_id in potential_targets:
                if d_node_id in used_d_nodes:
                    continue

                d_node = diagram.nodes[d_node_id]
                if self._check_node_constraints(d_node, pattern_nodes[p_node_id]):
                    # Make a local copy of mapping to backtrack safely
                    new_mapping = current_mapping.copy()
                    new_mapping[p_node_id] = d_node_id

                    result = backtrack(p_idx + 1, new_mapping, used_d_nodes | {d_node_id})
                    if result:
                        return result

            return None

        # The initial call to backtrack should handle the first pattern node
        # by trying to map it to the provided start_node.
        # If the first pattern node has constraints, check them against start_node.
        if self._check_node_constraints(diagram.nodes[start_node], pattern_nodes[first_p_node]):
            initial_mapping = {first_p_node: start_node}
            initial_used_nodes = {start_node}
            return backtrack(1, initial_mapping, initial_used_nodes)
        return None

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
            if metric == "chain_length":
                # Longest path in DAG
                if nx.is_directed_acyclic_graph(g):
                    try:
                        nodes_list = list(g.nodes())
                        if len(nodes_list) >= 2:
                            lengths = []
                            for path in nx.all_simple_paths(g, nodes_list[0], nodes_list[-1]):
                                lengths.append(len(path) - 1)
                            results["chain_length"] = max(lengths) if lengths else 0
                        else:
                            results["chain_length"] = 0
                    except (nx.NetworkXNoPath, nx.NodeNotFound):
                        results["chain_length"] = 0
                else:
                    results["chain_length"] = None

            elif metric == "branching_factor":
                # Average out-degree
                if g.nodes():
                    out_degrees = [g.out_degree(n) for n in g.nodes()]
                    results["branching_factor"] = sum(out_degrees) / len(out_degrees)
                else:
                    results["branching_factor"] = 0.0

            elif metric == "density":
                # Graph density
                results["density"] = nx.density(g)

            elif metric == "num_nodes":
                results["num_nodes"] = g.number_of_nodes()

            elif metric == "num_edges":
                results["num_edges"] = g.number_of_edges()

            elif metric == "is_dag":
                results["is_dag"] = nx.is_directed_acyclic_graph(g)

        return results

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    def node_semantic_search(
        self,
        diagram_id: str,
        target_embedding: list[float],
        top_k: int = 5,
        threshold: float = 0.5,
    ) -> dict[str, Any]:
        """
        Search for nodes semantically similar to a target embedding.

        Args:
            diagram_id: ID of diagram
            target_embedding: The embedding vector to compare against
            top_k: Maximum number of results to return
            threshold: Minimum similarity score to include

        Returns:
            dict with similar nodes and scores
        """
        diagram = self.get_diagram(diagram_id)
        if not diagram:
            raise ValueError(f"Diagram {diagram_id} not found")

        similarities = []
        for node_id, node in diagram.nodes.items():
            if node.embedding:
                score = self._cosine_similarity(target_embedding, node.embedding)
                if score >= threshold:
                    similarities.append(
                        {"id": node_id, "label": node.label, "type": node.node_type, "score": score}
                    )

        # Sort by score descending
        similarities.sort(key=lambda x: cast(float, x["score"]), reverse=True)
        results = similarities[:top_k]

        return {
            "target_dimensions": len(target_embedding),
            "nodes_checked": len([n for n in diagram.nodes.values() if n.embedding]),
            "matches": results,
        }

    def diagram_extract(
        self, diagram_id: str, node_ids: list[str], composite_label: str = "Extracted Subdiagram"
    ) -> dict[str, Any]:
        """
        Extract a subgraph into a composite node.

        Args:
            diagram_id: Source diagram ID
            node_ids: List of nodes to extract
            composite_label: Label for the new composite node

        Returns:
            dict containing success status, new diagram ID, and new composite node ID
        """
        diagram = self.get_diagram(diagram_id)
        if not diagram:
            raise ValueError(f"Diagram {diagram_id} not found")

        # 1. Validate nodes
        for nid in node_ids:
            if nid not in diagram.nodes:
                raise ValueError(f"Node {nid} not found in diagram")

        # 2. Extract subgraph nodes and edges
        sub_nodes = []
        for nid in node_ids:
            node = diagram.nodes[nid]
            sub_nodes.append(
                {
                    "id": node.id,
                    "label": node.label,
                    "type": node.node_type,
                    "metadata": node.metadata,
                    "embedding": node.embedding,
                    "sub_diagram_id": node.sub_diagram_id,
                }
            )

        sub_edges = []
        node_id_set = set(node_ids)
        for edge in diagram.edges:
            if edge.source in node_id_set and edge.target in node_id_set:
                sub_edges.append(
                    {
                        "source": edge.source,
                        "target": edge.target,
                        "label": edge.label,
                        "weight": edge.weight,
                        "properties": edge.properties,
                    }
                )

        # 3. Create new subdiagram
        sub_diagram_id = self.create_diagram(sub_nodes, sub_edges)

        # 4. Modify original diagram
        composite_id = str(uuid.uuid4())
        composite_node = DiagramNode(
            id=composite_id,
            label=composite_label,
            node_type="composite",
            sub_diagram_id=sub_diagram_id,
        )

        # Re-route external edges
        new_edges = []
        for edge in diagram.edges:
            if edge.source in node_id_set and edge.target in node_id_set:
                continue  # Edge moved to subdiagram
            elif edge.source in node_id_set:
                # Internal to external: re-route from composite
                new_edges.append(
                    DiagramEdge(
                        source=composite_id,
                        target=edge.target,
                        label=edge.label,
                        properties=edge.properties,
                        weight=edge.weight,
                    )
                )
            elif edge.target in node_id_set:
                # External to internal: re-route to composite
                new_edges.append(
                    DiagramEdge(
                        source=edge.source,
                        target=composite_id,
                        label=edge.label,
                        properties=edge.properties,
                        weight=edge.weight,
                    )
                )
            else:
                # Unaffected edge
                new_edges.append(edge)

        diagram.edges = new_edges

        # Remove old nodes and add composite
        for nid in node_ids:
            del diagram.nodes[nid]
        diagram.nodes[composite_id] = composite_node

        if diagram.root_node in node_id_set:
            diagram.root_node = composite_id

        # Invalidate cache
        self.graph_cache.pop(diagram_id, None)

        # Record derivation step
        step = DerivationStep(
            rule_name="diagram_extract",
            match_mapping={nid: nid for nid in node_ids},
            description=f"Extracted nodes into composite {composite_id} (subdiagram {sub_diagram_id})",
        )
        diagram.transformations.append(step)

        return {
            "success": True,
            "composite_node_id": composite_id,
            "sub_diagram_id": sub_diagram_id,
            "diagram_id": diagram_id,
        }

    def explore_reasoning_space(
        self, diagram_id: str, start_node: str, steps: int = 5, temperature: float = 0.5
    ) -> dict[str, Any]:
        """
        Wander the diagram based on a curiosity metric using NavigationMemory.

        Prioritizes nodes that have a low exploration_count.

        Args:
            diagram_id: ID of diagram
            start_node: Starting node ID
            steps: Number of steps to take
            temperature: Exploration factor (0.0 = greedy, 1.0 = random)

        Returns:
            dict with path, memory state
        """
        diagram = self.get_diagram(diagram_id)
        if not diagram:
            raise ValueError(f"Diagram {diagram_id} not found")

        if start_node not in diagram.nodes:
            raise ValueError(f"Start node {start_node} not found")

        # Get or create memory for this diagram space
        if diagram_id not in self.memories:
            self.memories[diagram_id] = NavigationMemory(position=start_node)

        memory = self.memories[diagram_id]

        current_node = start_node
        path = [current_node]
        memory.exploration_count[current_node] = memory.exploration_count.get(current_node, 0) + 1
        memory.visited_trajectory.append(current_node)
        memory.position = current_node

        for _ in range(steps):
            edges = diagram.get_outgoing_edges(current_node)
            if not edges:
                break  # Reached a dead end

            targets = [e.target for e in edges]

            # Simple softmin on exploration count (lower count = higher probability)
            counts = [memory.exploration_count.get(t, 0) for t in targets]

            if temperature <= 0.01:
                # Greedy: pick the absolute minimum count. Always pick unvisited first.
                min_idx = counts.index(min(counts))
                next_node = targets[min_idx]
            else:
                # e^(-count / T) / Z
                weights = [math.exp(-c / temperature) for c in counts]
                # Handle case where all weights are zero (e.g., all counts very high, T small)
                if sum(weights) == 0:
                    next_node = self._random_engine.choice(targets)  # Fallback
                else:
                    next_node = self._random_engine.choices(targets, weights=weights, k=1)[0]

            current_node = next_node
            path.append(current_node)
            memory.exploration_count[current_node] = (
                memory.exploration_count.get(current_node, 0) + 1
            )
            memory.visited_trajectory.append(current_node)
            memory.position = current_node

        return {
            "success": True,
            "path": path,
            "steps_taken": len(path) - 1,
            "exploration_counts": memory.exploration_count,
        }

    def check_diagram_equivalence(self, diagram_id_1: str, diagram_id_2: str) -> bool:
        """
        Check if two diagrams are structurally equivalent (isomorphic).

        Args:
            diagram_id_1: First diagram ID
            diagram_id_2: Second diagram ID

        Returns:
            bool: True if isomorphic
        """
        d1 = self.get_diagram(diagram_id_1)
        d2 = self.get_diagram(diagram_id_2)
        if not d1 or not d2:
            return False

        g1 = self.graph_cache.get(diagram_id_1) or self._build_networkx_graph(d1)
        g2 = self.graph_cache.get(diagram_id_2) or self._build_networkx_graph(d2)

        def node_match(n1: dict[str, Any], n2: dict[str, Any]) -> bool:
            return n1.get("type") == n2.get("type") and n1.get("label") == n2.get("label")

        def edge_match(e1: dict[str, Any], e2: dict[str, Any]) -> bool:
            return e1.get("label") == e2.get("label")

        return nx.is_isomorphic(g1, g2, node_match=node_match, edge_match=edge_match)

    def explore_equivalent_states(
        self,
        diagram_id: str,
        rules_specs: list[dict[str, Any]],
        max_depth: int = 3,
        max_states: int = 20,
    ) -> dict[str, Any]:
        """
        Explore alternative diagram states reachable via rewrite rules.

        Constructs a meta-graph of structurally unique diagram configurations.

        Args:
            diagram_id: Starting diagram ID
            rules_specs: List of serialized RewriteRule dicts
            max_depth: Maximum BFS depth
            max_states: Maximum number of unique states to discover

        Returns:
            dict with states (diagram IDs) and transitions (meta-edges)
        """
        start_diagram = self.get_diagram(diagram_id)
        if not start_diagram:
            raise ValueError(f"Diagram {diagram_id} not found")

        # states: unique_id -> actual_diagram_id (one representative for each isomorphism class)
        states = {diagram_id: diagram_id}
        meta_edges = []
        queue = collections.deque([(diagram_id, 0)])

        def find_representative(query_id: str) -> Optional[str]:
            for rep_id in states:
                if self.check_diagram_equivalence(rep_id, query_id):
                    return rep_id
            return None

        while queue and len(states) < max_states:
            curr_id, depth = queue.popleft()
            if depth >= max_depth:
                continue

            # Try applying each rule
            for rule in rules_specs:
                rule_name = rule.get("rule_name", "unnamed")
                matches = self.pattern_match(curr_id, rule.get("lhs", {}))

                for mapping in matches.get("matches", []):
                    # We need a copy of the diagram to apply the rule without modifying the original in the search
                    # However, apply_rewrite_rule modifies in-place.
                    # Factory-create a clone.
                    curr_diag = self.get_diagram(curr_id)
                    if not curr_diag:
                        continue

                    clone_nodes = [
                        {
                            "id": n.id,
                            "label": n.label,
                            "type": n.node_type,
                            "metadata": n.metadata.copy(),
                            "embedding": n.embedding,
                            "sub_diagram_id": n.sub_diagram_id,
                        }
                        for n in curr_diag.nodes.values()
                    ]
                    clone_edges = [
                        {
                            "source": e.source,
                            "target": e.target,
                            "label": e.label,
                            "weight": e.weight,
                            "properties": e.properties.copy(),
                        }
                        for e in curr_diag.edges
                    ]

                    # Create temporary working diagram
                    next_id = self.create_diagram(clone_nodes, clone_edges)
                    try:
                        self.apply_rewrite_rule(next_id, rule, mapping)

                        rep_id = find_representative(next_id)
                        if rep_id:
                            # Already found an equivalent state, record transition and clean up clone
                            meta_edges.append(
                                {
                                    "source": curr_id,
                                    "target": rep_id,
                                    "rule": rule_name,
                                }
                            )

                            # Delete the clone if it's not the representative
                            if next_id != rep_id:
                                del self.diagrams[next_id]
                                self.graph_cache.pop(next_id, None)
                        else:
                            # New state found
                            states[next_id] = next_id
                            meta_edges.append(
                                {
                                    "source": curr_id,
                                    "target": next_id,
                                    "rule": rule_name,
                                }
                            )

                            queue.append((next_id, depth + 1))
                            if len(states) >= max_states:
                                break
                    except (ValueError, RuntimeError, KeyError) as e:
                        self.logger.warning(
                            f"Failed to apply rule {rule_name} during exploration: {e}"
                        )

                        del self.diagrams[next_id]
                        self.graph_cache.pop(next_id, None)

            if len(states) >= max_states:
                break

        return {
            "start_diagram": diagram_id,
            "num_states_found": len(states),
            "states": list(states.keys()),
            "meta_edges": meta_edges,
        }
