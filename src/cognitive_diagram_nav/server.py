"""
MCP Server implementation for Cognitive Diagram Navigation.

Exposes tools for diagram creation, navigation, pattern matching, and reasoning
through the Model Context Protocol.
"""

import sys
from typing import Any

import structlog
from mcp.server.fastmcp import FastMCP

from .graph_engine import GraphEngine

# Configure structlog
structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
    cache_logger_on_first_use=True,
)
logger = structlog.get_logger(__name__)

# Initialize MCP server
server = FastMCP("cognitive-diagram-nav-mcp")

# Initialize graph engine (singleton for server lifetime)
graph_engine = GraphEngine(max_diagrams=100)


# ============================================================================
# Tool: Diagram Management
# ============================================================================


@server.tool()
def diagram_create(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Create a new diagram with specified nodes and edges.

    A diagram is the primary unit of reasoning, representing a directed acyclic graph.

    Args:
        nodes: List of node specifications. Each must have:
            - id: Unique identifier (string)
            - label: Human-readable label (string)
            - type: One of 'operation', 'terminal', 'control', 'composite'
            - metadata: Optional dict of additional properties
            - embedding: Optional list of floats for semantic search

        edges: List of edge specifications. Each must have:
            - source: Source node ID (string)
            - target: Target node ID (string)
            - label: Relationship label (string)
            - weight: Optional numeric weight (default: 1.0)
            - properties: Optional dict of additional properties

    Returns:
        dict with diagram_id, num_nodes, num_edges, validity
    """
    try:
        logger.info(f"Creating diagram with {len(nodes)} nodes and {len(edges)} edges")
        diagram_id = graph_engine.create_diagram(nodes, edges)
        diagram = graph_engine.get_diagram(diagram_id)

        if not diagram:
            raise RuntimeError("Failed to retrieve created diagram")

        return {
            "success": True,
            "diagram_id": diagram_id,
            "num_nodes": diagram.num_nodes(),
            "num_edges": diagram.num_edges(),
            "validity": diagram.is_valid(),
            "root_node": diagram.root_node,
        }
    except (ValueError, RuntimeError) as e:
        logger.error("Error creating diagram", error=str(e), node_count=len(nodes), exc_info=True)
        return {
            "success": False,
            "error": str(e),
        }


@server.tool()
def diagram_load(diagram_id: str) -> dict[str, Any]:
    """
    Load and return complete diagram structure.

    Args:
        diagram_id: ID of diagram to load

    Returns:
        dict with full diagram structure or error
    """
    try:
        diagram = graph_engine.get_diagram(diagram_id)
        if not diagram:
            return {
                "success": False,
                "error": f"Diagram {diagram_id} not found",
            }

        return {
            "success": True,
            "diagram_id": diagram.diagram_id,
            "num_nodes": diagram.num_nodes(),
            "num_edges": diagram.num_edges(),
            "root_node": diagram.root_node,
            "nodes": [
                {
                    "id": node.id,
                    "label": node.label,
                    "type": node.node_type,
                    "metadata": node.metadata,
                }
                for node in diagram.nodes.values()
            ],
            "edges": [
                {
                    "source": edge.source,
                    "target": edge.target,
                    "label": edge.label,
                    "weight": edge.weight,
                    "properties": edge.properties,
                }
                for edge in diagram.edges
            ],
            "invariants": diagram.invariants,
            "transformations": [
                {
                    "rule_name": step.rule_name,
                    "match_mapping": step.match_mapping,
                    "timestamp": step.timestamp,
                    "description": step.description,
                    "diagram_before": step.diagram_before,
                    "diagram_after": step.diagram_after,
                }
                for step in diagram.transformations
            ],
        }
    except (ValueError, RuntimeError) as e:
        logger.error("Error loading diagram", diagram_id=diagram_id, error=str(e), exc_info=True)
        return {
            "success": False,
            "error": str(e),
        }


# ============================================================================
# Tool: Graph Navigation
# ============================================================================


@server.tool()
def navigate_breadth_first(
    diagram_id: str,
    start_node: str,
    max_depth: int = 5,
    expand_composites: bool = False,
) -> dict[str, Any]:
    """
    Explore diagram structure using breadth-first traversal.

    Systematically visits nodes level by level, useful for understanding structure.

    Args:
        diagram_id: ID of diagram to explore
        start_node: Starting node ID
        max_depth: Maximum exploration depth (default: 5)

    Returns:
        dict with explored_nodes, edges_traversed, total_explored
    """
    try:
        logger.info(
            "BFS exploration",
            diagram_id=diagram_id,
            start_node=start_node,
            expand_composites=expand_composites,
        )
        result = graph_engine.navigate_breadth_first(
            diagram_id, start_node, max_depth, expand_composites
        )
        return {
            "success": True,
            **result,
        }
    except ValueError as e:
        logger.error(
            "Error in BFS navigation",
            diagram_id=diagram_id,
            start_node=start_node,
            error=str(e),
            exc_info=True,
        )
        return {
            "success": False,
            "error": str(e),
        }


@server.tool()
def navigate_guided(
    diagram_id: str,
    start_node: str,
    goal_node: str,
    heuristic: str = "distance",
    expand_composites: bool = False,
) -> dict[str, Any]:
    """
    Find guided path from start to goal node.

    Uses shortest-path algorithm for optimal traversal.

    Args:
        diagram_id: ID of diagram
        start_node: Starting node ID
        goal_node: Target node ID
        heuristic: 'distance' (default), 'reward', or 'semantic_similarity'

    Returns:
        dict with path, cost, num_steps, found flag
    """
    try:
        logger.info(
            "Guided navigation",
            diagram_id=diagram_id,
            start_node=start_node,
            goal_node=goal_node,
            expand_composites=expand_composites,
        )
        result = graph_engine.navigate_guided(
            diagram_id, start_node, goal_node, heuristic, expand_composites
        )
        return {
            "success": True,
            **result,
        }
    except ValueError as e:
        logger.error(
            "Error in guided navigation",
            diagram_id=diagram_id,
            start_node=start_node,
            goal_node=goal_node,
            error=str(e),
            exc_info=True,
        )
        return {
            "success": False,
            "error": str(e),
        }


@server.tool()
def analyze_reachability(
    diagram_id: str,
    source: str,
    targets: list[str] | None = None,
) -> dict[str, Any]:
    """
    Analyze reachability from source node.

    Computes all nodes reachable from source and their distances.

    Args:
        diagram_id: ID of diagram
        source: Source node ID
        targets: Optional specific nodes to check

    Returns:
        dict with reachable_nodes list, distances, target_reachability
    """
    try:
        logger.info(f"Reachability analysis of {diagram_id} from {source}")
        result = graph_engine.analyze_reachability(diagram_id, source, targets)
        return {
            "success": True,
            **result,
        }
    except ValueError as e:
        logger.error(
            "Error in reachability analysis",
            diagram_id=diagram_id,
            source=source,
            error=str(e),
            exc_info=True,
        )
        return {
            "success": False,
            "error": str(e),
        }


@server.tool()
def explore_reasoning_space(
    diagram_id: str,
    start_node: str,
    steps: int = 5,
    temperature: float = 0.5,
) -> dict[str, Any]:
    """
    Wander the diagram based on a curiosity metric using NavigationMemory.

    Prioritizes nodes that have a low exploration_count.

    Args:
        diagram_id: ID of diagram
        start_node: Starting node ID
        steps: Number of steps to take (default: 5)
        temperature: Exploration factor (0.0 = greedy unvisited, 1.0 = highly random)

    Returns:
        dict with path, steps_taken, and updated exploration_counts
    """
    try:
        logger.info(
            "Curious exploration",
            diagram_id=diagram_id,
            start_node=start_node,
            steps=steps,
            temperature=temperature,
        )
        result = graph_engine.explore_reasoning_space(diagram_id, start_node, steps, temperature)
        return {
            "success": True,
            **result,
        }
    except ValueError as e:
        logger.error(
            "Error in exploratory navigation",
            diagram_id=diagram_id,
            start_node=start_node,
            error=str(e),
            exc_info=True,
        )
        return {
            "success": False,
            "error": str(e),
        }


@server.tool()
def diagram_extract(
    diagram_id: str, node_ids: list[str], composite_label: str = "Extracted Subdiagram"
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
    try:
        logger.info(f"Extracting subgraph from {diagram_id}")
        result = graph_engine.diagram_extract(diagram_id, node_ids, composite_label)
        return result
    except ValueError as e:
        logger.error(
            "Error extracting subgraph",
            diagram_id=diagram_id,
            node_ids=node_ids,
            error=str(e),
            exc_info=True,
        )
        return {
            "success": False,
            "error": str(e),
        }


# ============================================================================
# Tool: Pattern Matching & Rewriting
# ============================================================================


@server.tool()
def apply_rewrite_rule(
    diagram_id: str,
    rule_spec: dict[str, Any],
    match_mapping: dict[str, str],
) -> dict[str, Any]:
    """
    Apply a formal Double-Pushout (DPO) rewrite rule to a diagram.

    Args:
        diagram_id: Target diagram ID
        rule_spec: Serialize RewriteRule dict with 'lhs' and 'rhs' patterns
        match_mapping: Mapping of rule LHS node IDs to diagram node IDs (from pattern_match)

    Returns:
        dict containing success status and modified diagram stats
    """
    try:
        rule_name = rule_spec.get("rule_name", "Unnamed Rule")
        logger.info(f"Applying rewrite rule '{rule_name}' to {diagram_id}")

        result = graph_engine.apply_rewrite_rule(diagram_id, rule_spec, match_mapping)
        return {
            "success": True,
            **result,
        }
    except ValueError as e:
        logger.error(
            "Error applying rewrite rule",
            diagram_id=diagram_id,
            rule_name=rule_name,
            error=str(e),
            exc_info=True,
        )
        return {
            "success": False,
            "error": str(e),
        }


@server.tool()
def export_proof(diagram_id: str, output_format: str = "text") -> dict[str, Any]:
    """
    Export a diagram's transformation history as a structured proof.

    Args:
        diagram_id: ID of diagram to export proof for
        output_format: 'text' (natural language) or 'json' (structured)

    Returns:
        dict with proof steps and metadata
    """
    try:
        diagram = graph_engine.get_diagram(diagram_id)
        if not diagram:
            return {"success": False, "error": f"Diagram {diagram_id} not found"}

        if output_format == "json":
            steps = [
                {
                    "rule_name": s.rule_name,
                    "match_mapping": s.match_mapping,
                    "timestamp": s.timestamp,
                    "description": s.description,
                }
                for s in diagram.transformations
            ]
            return {"success": True, "diagram_id": diagram_id, "steps": steps}

        # Default: text format
        lines = [f"Proof Derivation for Diagram {diagram_id}:"]
        for i, s in enumerate(diagram.transformations, 1):
            lines.append(f"{i}. {s.description or f'Applied {s.rule_name}'}")

        return {"success": True, "diagram_id": diagram_id, "proof": "\n".join(lines)}
    except ValueError as e:
        logger.error("Error exporting proof", diagram_id=diagram_id, error=str(e), exc_info=True)
        return {"success": False, "error": str(e)}


@server.tool()
def check_diagram_equivalence(diagram_id_1: str, diagram_id_2: str) -> dict[str, Any]:
    """
    Check if two diagrams are structurally equivalent (isomorphic).

    Args:
        diagram_id_1: First diagram ID
        diagram_id_2: Second diagram ID

    Returns:
        dict with equivalence status
    """
    try:
        logger.info(f"Checking equivalence between {diagram_id_1} and {diagram_id_2}")
        is_equivalent = graph_engine.check_diagram_equivalence(diagram_id_1, diagram_id_2)
        return {
            "success": True,
            "is_equivalent": is_equivalent,
        }
    except ValueError as e:
        logger.error("Error checking equivalence", error=str(e), exc_info=True)
        return {"success": False, "error": str(e)}


@server.tool()
def explore_equivalent_states(
    diagram_id: str,
    rules: list[dict[str, Any]],
    max_depth: int = 3,
    max_states: int = 20,
) -> dict[str, Any]:
    """
    Explore alternative diagram states reachable via rewrite rules.

    Constructs a meta-graph of structurally unique diagram configurations.

    Args:
        diagram_id: Starting diagram ID
        rules: List of serialized RewriteRule dicts
        max_depth: Maximum BFS depth
        max_states: Maximum number of unique states to discover

    Returns:
        dict with metadata about discovery and unique states
    """
    try:
        logger.info(f"Exploring state space for {diagram_id} with {len(rules)} rules")
        result = graph_engine.explore_equivalent_states(diagram_id, rules, max_depth, max_states)
        return {
            "success": True,
            **result,
        }
    except ValueError as e:
        logger.error(
            "Error exploring equivalent states",
            diagram_id=diagram_id,
            error=str(e),
            exc_info=True,
        )
        return {"success": False, "error": str(e)}


@server.tool()
def pattern_match(
    diagram_id: str,
    pattern: dict[str, Any],
) -> dict[str, Any]:
    """
    Find all pattern matches within a diagram.

    Implements subgraph matching to locate structural patterns.

    Args:
        diagram_id: ID of diagram to search
        pattern: Pattern spec with 'nodes' (dict) and 'edges' (list)
            Each edge tuple: (source_id, target_id, constraints_dict)

    Returns:
        dict with matches list, num_matches
    """
    try:
        logger.info(f"Pattern matching in {diagram_id}")
        result = graph_engine.pattern_match(diagram_id, pattern)
        return {
            "success": True,
            **result,
        }
    except ValueError as e:
        logger.error(
            "Error in pattern matching",
            diagram_id=diagram_id,
            error=str(e),
            exc_info=True,
        )
        return {
            "success": False,
            "error": str(e),
        }


# ============================================================================
# Tool: Analysis & Metrics
# ============================================================================


@server.tool()
def compute_metrics(
    diagram_id: str,
    metrics: list[str],
) -> dict[str, Any]:
    """
    Compute structural metrics on diagram.

    Computes graph-theoretic properties useful for understanding complexity.

    Args:
        diagram_id: ID of diagram
        metrics: List of metrics to compute. Options:
            - 'chain_length': Longest path in DAG
            - 'branching_factor': Average out-degree
            - 'density': Overall connectivity
            - 'num_nodes': Node count
            - 'num_edges': Edge count
            - 'is_dag': Whether diagram is acyclic

    Returns:
        dict with computed metrics
    """
    try:
        logger.info(f"Computing metrics for {diagram_id}: {metrics}")
        result = graph_engine.compute_metrics(diagram_id, metrics)
        return {
            "success": True,
            "metrics": result,
        }
    except ValueError as e:
        logger.error(
            "Error computing metrics",
            diagram_id=diagram_id,
            metrics=metrics,
            error=str(e),
            exc_info=True,
        )
        return {
            "success": False,
            "error": str(e),
        }


@server.tool()
def node_semantic_search(
    diagram_id: str,
    target_embedding: list[float],
    top_k: int = 5,
    threshold: float = 0.5,
) -> dict[str, Any]:
    """
    Search for nodes semantically similar to a target embedding.

    Args:
        diagram_id: ID of diagram
        target_embedding: The embedding vector (list of floats) to compare against
        top_k: Maximum number of results to return (default: 5)
        threshold: Minimum cosine similarity score to include (default: 0.5)

    Returns:
        dict with similar nodes and similarity scores
    """
    try:
        logger.info(f"Semantic search in {diagram_id} for top {top_k} matches")
        result = graph_engine.node_semantic_search(diagram_id, target_embedding, top_k, threshold)
        return {
            "success": True,
            **result,
        }
    except ValueError as e:
        logger.error(
            "Error in semantic search",
            diagram_id=diagram_id,
            top_k=top_k,
            error=str(e),
            exc_info=True,
        )
        return {
            "success": False,
            "error": str(e),
        }


# ============================================================================
# Tool: Server Info & Discovery
# ============================================================================


@server.tool()
def server_info() -> dict[str, Any]:
    """
    Return server capabilities and status information.

    Returns:
        dict with version, capabilities, active_diagrams, resources
    """
    return {
        "name": "Cognitive Diagram Navigation MCP",
        "version": "0.1.0",
        "capabilities": [
            "diagram_creation",
            "graph_navigation",
            "pattern_matching",
            "metric_computation",
            "reachability_analysis",
            "proof_export",
            "state_space_exploration",
            "structural_equivalence",
        ],
        "active_diagrams": len(graph_engine.diagrams),
        "max_diagrams": graph_engine.max_diagrams,
        "tools": [
            "diagram_create",
            "diagram_load",
            "navigate_breadth_first",
            "navigate_guided",
            "analyze_reachability",
            "explore_reasoning_space",
            "diagram_extract",
            "pattern_match",
            "apply_rewrite_rule",
            "export_proof",
            "check_diagram_equivalence",
            "explore_equivalent_states",
            "compute_metrics",
            "server_info",
        ],
    }


def main() -> None:
    """Main entry point for the MCP server."""
    logger.info("Starting Cognitive Diagram Navigation MCP server...")
    server.run()


if __name__ == "__main__":
    main()
