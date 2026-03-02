# Cognitive Diagram Navigation MCP Server

An advanced MCP server implementing **diagrammatic reasoning** with **memory-augmented spatial exploration**, enabling structured chain-of-thought reasoning through visual reasoning spaces.

## Overview

This MCP server combines three research domains:

1. **Diagrammatic Reasoning** (Quantomatic-inspired)
   - String diagrams for formal proof construction
   - Graph rewriting with double-pushout semantics
   - Pattern matching and structural transformation

2. **Cognitive Navigation** (Hippocampal-inspired)
   - Place cell-like encoding of reasoning points
   - Reward-based spatial navigation
   - Memory-augmented exploration of reasoning spaces

3. **Chain-of-Thought Reasoning**
   - Sequential logic bonds stronger than keywords
   - Multi-step derivation tracking
   - Formal proof verification

## Features

### Core Capabilities

- **Diagram Creation**: Build reasoning graphs from node/edge specifications
- **Guided Navigation**: Find optimal paths through reasoning spaces
- **Breadth-First Exploration**: Systematically discover diagram structure
- **Pattern Matching**: Locate subgraph patterns for rule application
- **Reachability Analysis**: Understand connectivity and distance metrics
- **Structural Metrics**: Compute graph properties (chain length, branching factor, etc.)

### Design Principles

- **Memory-Augmented**: Tracks navigation history and position encoding
- **Compositional**: Build complex reasoning from simpler diagrams
- **Verifiable**: All transformations produce formal proof chains
- **Extensible**: Pattern-based rewriting allows domain-specific rules

## Installation

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager (recommended)

### Setup

```bash
# Clone the repository
cd cognitive-diagram-nav-mcp

# Create virtual environment with uv
uv venv

# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install project in development mode
uv pip install -e ".[dev]"

# Or with just the MCP dependencies
uv pip install -e .
```

## Usage

### Starting the Server

```bash
# Using uv
uv run src/cognitive_diagram_nav/server.py

# Or with Python directly
python src/cognitive_diagram_nav/server.py
```

The server will start on stdio by default and be ready to accept MCP connections.

### Configuring with Claude

Add to your Claude configuration (usually `~/.config/Claude/claude_desktop_config.json` or `%AppData%\Claude\claude_desktop_config.json` on Windows):

```json
{
  "mcpServers": {
    "cognitive-diagram-nav": {
      "command": "uv",
      "args": [
        "--directory",
        "/your-path-to/cognitive-diagram-nav-mcp",
        "run",
        "cognitive-diagram-nav"
      ]
    }
  }
}
```

Replace `/path/to/` with the actual path to the project.

## Examples

### Example 1: Create and Navigate a Simple Diagram

```python
# This would be executed through Claude's MCP interface

# Create a simple reasoning diagram
diagram = diagram_create(
    nodes=[
        {"id": "premise1", "label": "Premise 1", "type": "terminal"},
        {"id": "logic", "label": "Logical operation", "type": "operation"},
        {"id": "conclusion", "label": "Conclusion", "type": "terminal"},
    ],
    edges=[
        {"source": "premise1", "target": "logic", "label": "input"},
        {"source": "logic", "target": "conclusion", "label": "output"},
    ]
)
# Returns: diagram_id = "abc123..."

# Explore the diagram
result = navigate_breadth_first(
    diagram_id="abc123...",
    start_node="premise1",
    max_depth=3
)
# Shows connected nodes and structure
```

### Example 2: Find Optimal Path

```python
# Find shortest reasoning path
path_result = navigate_guided(
    diagram_id="abc123...",
    start_node="premise1",
    goal_node="conclusion",
    heuristic="distance"
)
# Returns path with cost and steps
```

### Example 3: Analyze Reachability

```python
# Understand what can be reached from a starting point
reachability = analyze_reachability(
    diagram_id="abc123...",
    source="premise1",
    targets=["logic", "conclusion"]
)
# Shows all reachable nodes and distances
```

## Architecture

### Components

```
┌─────────────────────────────────┐
│   MCP Client (Claude/LLM)       │
└────────────────┬────────────────┘
                 │ JSON-RPC 2.0
┌────────────────▼────────────────┐
│   FastMCP Server                │
├─────────────────────────────────┤
│   Tools Layer (MCP Interface)   │
├─────────────────────────────────┤
│   GraphEngine (Core Logic)      │
│   - Navigation                  │
│   - Pattern Matching            │
│   - Metrics                     │
├─────────────────────────────────┤
│   Models (Data Structures)      │
│   - Diagram                     │
│   - Pattern                     │
│   - NavigationMemory            │
└─────────────────────────────────┘
```

### Key Classes

- `Diagram`: Complete reasoning graph with nodes, edges, and metadata
- `GraphEngine`: Core reasoning engine with navigation and analysis
- `Pattern`: Specification for pattern matching in diagrams
- `NavigationMemory`: Tracks position and history during exploration

## Development

### Running Tests

```bash
# Run all tests
uv run pytest

# With coverage
uv run pytest --cov=src/cognitive_diagram_nav

# Specific test
uv run pytest tests/test_models.py
```

### Code Quality

```bash
# Format code
uv run black src tests

# Lint
uv run ruff check src tests

# Type checking
uv run mypy src
```

### Building Documentation

```bash
cd docs
uv run sphinx-build -b html . _build
```

## Roadmap

### Phase 1: Foundation (Current)
- [x] Core data structures (Diagram, Pattern, NavigationMemory)
- [x] GraphEngine implementation
- [x] Basic MCP tools (create, load, navigate)
- [ ] Comprehensive testing

### Phase 2: Advanced Navigation
- [ ] Memory-augmented exploration with vectorized embeddings
- [ ] Hierarchical reasoning with diagram composition
- [ ] Approximate algorithms for large graphs

### Phase 3: Pattern & Rewriting
- [ ] Unification-based pattern matching
- [ ] Double-pushout (DPO) rewriting
- [ ] Rule system and simplification strategies

### Phase 4: Reasoning Integration
- [ ] Proof derivation chain construction
- [ ] Equivalence checking
- [ ] Reasoning space exploration

### Phase 5: Production
- [ ] Performance optimization
- [ ] Persistence layer
- [ ] Advanced error handling
- [ ] Monitoring and observability

## Security Considerations

- **Input Validation**: All diagram specifications validated before processing
- **Resource Limits**: Max diagrams and exploration depth configurable
- **Error Handling**: Comprehensive exception handling with logging
- **Isolation**: Each diagram is independent; no cross-contamination

## Performance Notes

- **Scalability**: Designed to handle 100s-1000s of nodes efficiently
- **Memory**: In-memory storage; configurable max diagram count
- **Algorithms**: Uses NetworkX for optimized graph operations
- **Caching**: NetworkX graphs cached after initial construction

## References

- Kissinger & Zamdzhiev (2015): "Quantomatic: A Proof Assistant for Diagrammatic Reasoning"
- Hippocampal place cells and reward-based navigation research
- Chain-of-Thought prompting literature
- Model Context Protocol (MCP) specification

## License

MIT - See LICENSE file

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Ensure tests pass and code is formatted
4. Submit a pull request

## Contact

For questions or feedback about this MCP server, please open an issue on GitHub.

---

**Status**: Alpha (v0.1.0) - Core functionality complete, testing and optimization in progress.
