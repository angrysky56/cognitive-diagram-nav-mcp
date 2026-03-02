"""
MCP Server implementation for Cognitive Diagram Navigation.

Exposes tools for diagram creation, navigation, pattern matching, and reasoning
through the Model Context Protocol.
"""

import sys
import structlog
from typing import Any

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
            'success': True,
            'diagram_id': diagram_id,
            'num_nodes': diagram.num_nodes(),
            'num_edges': diagram.num_edges(),
            'validity': diagram.is_valid(),
            'root_node': diagram.root_node,
        }
    except Exception as e:
        logger.error(f"Error creating diagram: {e}")
        return {
            'success': False,
            'error': str(e),
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
                'success': False,
                'error': f'Diagram {diagram_id} not found',
            }

        return {
            'success': True,
            'diagram_id': diagram.diagram_id,
            'num_nodes': diagram.num_nodes(),
            'num_edges': diagram.num_edges(),
            'root_node': diagram.root_node,
            'nodes': [
                {
                    'id': node.id,
                    'label': node.label,
                    'type': node.node_type,
                    'metadata': node.metadata,
                }
                for node in diagram.nodes.values()
            ],
            'edges': [
                {
                    'source': edge.source,
                    'target': edge.target,
                    'label': edge.label,
                    'weight': edge.weight,
                    'properties': edge.properties,
                }
                for edge in diagram.edges
            ],
            'invariants': diagram.invariants,
            'transformations': diagram.transformations,
        }
    except Exception as e:
        logger.error(f"Error loading diagram: {e}")
        return {
            'success': False,
            'error': str(e),
        }


# ============================================================================
# Tool: Graph Navigation
# ============================================================================


@server.tool()
def navigate_breadth_first(
    diagram_id: str,
    start_node: str,
    max_depth: int = 5,
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
        logger.info(f"BFS exploration of {diagram_id} from {start_node}")
        result = graph_engine.navigate_breadth_first(diagram_id, start_node, max_depth)
        return {
            'success': True,
            **result,
        }
    except Exception as e:
        logger.error(f"Error in BFS navigation: {e}")
        return {
            'success': False,
            'error': str(e),
        }


@server.tool()
def navigate_guided(
    diagram_id: str,
    start_node: str,
    goal_node: str,
    heuristic: str = 'distance',
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
        logger.info(f"Guided navigation in {diagram_id}: {start_node} → {goal_node}")
        result = graph_engine.navigate_guided(
            diagram_id, start_node, goal_node, heuristic
        )
        return {
            'success': True,
            **result,
        }
    except Exception as e:
        logger.error(f"Error in guided navigation: {e}")
        return {
            'success': False,
            'error': str(e),
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
            'success': True,
            **result,
        }
    except Exception as e:
        logger.error(f"Error in reachability analysis: {e}")
        return {
            'success': False,
            'error': str(e),
        }


# ============================================================================
# Tool: Pattern Matching
# ============================================================================


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
            'success': True,
            **result,
        }
    except Exception as e:
        logger.error(f"Error in pattern matching: {e}")
        return {
            'success': False,
            'error': str(e),
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
            'success': True,
            'metrics': result,
        }
    except Exception as e:
        logger.error(f"Error computing metrics: {e}")
        return {
            'success': False,
            'error': str(e),
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
        result = graph_engine.node_semantic_search(
            diagram_id, target_embedding, top_k, threshold
        )
        return {
            'success': True,
            **result,
        }
    except Exception as e:
        logger.error(f"Error in semantic search: {e}")
        return {
            'success': False,
            'error': str(e),
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
        'name': 'Cognitive Diagram Navigation MCP',
        'version': '0.1.0',
        'capabilities': [
            'diagram_creation',
            'graph_navigation',
            'pattern_matching',
            'metric_computation',
            'reachability_analysis',
        ],
        'active_diagrams': len(graph_engine.diagrams),
        'max_diagrams': graph_engine.max_diagrams,
        'tools': [
            'diagram_create',
            'diagram_load',
            'navigate_breadth_first',
            'navigate_guided',
            'analyze_reachability',
            'pattern_match',
            'compute_metrics',
            'server_info',
        ],
    }


def main() -> None:
    """Main entry point for the MCP server."""
    logger.info("Starting Cognitive Diagram Navigation MCP server...")
    server.run()


if __name__ == '__main__':
    main()
