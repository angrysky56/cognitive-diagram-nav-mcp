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
- **Pattern Matching**: Locate subgraph patterns for formal rule application
- **Double-Pushout (DPO) Rewriting**: Apply formal structural transformations
- **Hierarchical Reasoning**: Extract sub-diagrams into composite nodes
- **Reachability Analysis**: Understand connectivity and distance metrics
- **Structural Metrics**: Compute graph properties (chain length, branching factor, etc.)

### Advanced Reasoning

- **Proof Derivation**: Automatic tracking of transformation history
- **Proof Export**: Export structured or natural language proof chains
- **Equivalence Checking**: Verify if two diagrams are structurally identical (isomorphic)
- **State Space Exploration**: Discover all possible diagrams reachable via a set of rules
- **Curiosity-Driven Exploration**: Wander reasoning spaces based on "surprise" metrics

### Production Features

- **Automatic Persistence**: Diagrams are automatically saved to disk as JSON
- **LRU Memory Management**: Efficiently manages memory by evicting least-recently used diagrams
- **Persistence Management**: Tools to manually save, list, and delete diagrams on disk
- **Encrypted/Safe Randomization**: Uses `SystemRandom` for non-cryptographic but robust stochasticity

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

## Persistence

By default, the server persists diagrams to the local filesystem:

- **Location**: `~/.cognitive_diagram_nav/diagrams/`
- **Format**: JSON with full structural and transformation metadata.
- **LRU Cache**: Memory is managed using an LRU policy (default 100 diagrams); diagrams are seamlessly reloaded from disk on demand.

## Tools

| Category       | Tool                        | Description                             |
| -------------- | --------------------------- | --------------------------------------- |
| **Management** | `diagram_create`            | Create a new diagram                    |
|                | `diagram_load`              | Load diagram structure from memory/disk |
|                | `diagram_save`              | Force immediate sync to disk            |
|                | `diagram_list_saved`        | List all diagram IDs on disk            |
|                | `diagram_delete`            | Permanently remove from memory and disk |
| **Navigation** | `navigate_breadth_first`    | Level-by-level exploration              |
|                | `navigate_guided`           | Target-guided shortest path             |
|                | `analyze_reachability`      | Connectivity and distance analysis      |
|                | `explore_reasoning_space`   | Curiosity-based wandering               |
| **Reasoning**  | `pattern_match`             | Find structural patterns                |
|                | `apply_rewrite_rule`        | Apply formal DPO transformation         |
|                | `diagram_extract`           | Abstract subgraph into composite node   |
|                | `export_proof`              | View transformation history as proof    |
|                | `check_diagram_equivalence` | Check for isomorphism                   |
|                | `explore_equivalent_states` | Generate state-space from rules         |
| **Metrics**    | `compute_metrics`           | Graph-theoretic complexity metrics      |
|                | `node_semantic_search`      | Search nodes by vector embedding        |
|                | `server_info`               | Metadata and capability discovery       |

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
│   - Navigation & Exploration    │
│   - DPO Rewriting & Matching    │
│   - Memory & LRU Caching        │
├─────────────────────────────────┤
│   StorageManager (Persistence)  │
│   - JSON Serialization          │
│   - Disk I/O (Async Syncing)    │
├─────────────────────────────────┤
│   Models (Data Structures)      │
│   - Diagram / Node / Edge       │
│   - DerivationStep (Proofs)     │
│   - NavigationMemory            │
└─────────────────────────────────┘
```

### Key Classes

- `Diagram`: Complete reasoning graph with nodes, edges, and transformation metadata.
- `GraphEngine`: Core reasoning engine with navigation, DPO rewriting, and LRU cache.
- `StorageManager`: Handles atomic JSON serialization and disk persistence.
- `Pattern`: Specification for structural subgraph matching.
- `NavigationMemory`: Tracks traversal history and position for curiosity-based exploration.
- `DerivationStep`: Represents a single transformation for formal proof tracking.

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

### Phase 1: Foundation ✅

- [x] Core data structures (Diagram, Pattern, NavigationMemory)
- [x] GraphEngine implementation
- [x] Basic MCP tools (create, load, navigate)
- [x] Comprehensive testing (Pytest suite)

### Phase 2: Advanced Navigation ✅

- [x] Memory-augmented exploration with vectorized embeddings
- [x] Hierarchical reasoning with diagram composition
- [x] Vector-assisted search and guided navigation

### Phase 3: Pattern & Rewriting ✅

- [x] Structural pattern matching
- [x] Double-pushout (DPO) rewriting mathematical engine

### Phase 4: Reasoning Integration ✅

- [x] Proof derivation chain construction
- [x] Isomorphism checking (Structural Equivalence)
- [x] State-space exploration (Reasoning Space Discovery)

### Phase 5: Production & Resilience ✅

- [x] Persistence layer (Atomic JSON Storage)
- [x] LRU Eviction Policy
- [x] Advanced error handling & Resilience Audit
- [x] Fully typed and lint-clean codebase

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

**Status**: Beta (v0.5.0) - Core reasoning, production persistence, and advanced DPO transformations complete.

Live Demo Trace:
Creation: Built a logic diagram for $(A \land B) \to (B \land A)$.
Exploration: Used the curiosity-based explore_reasoning_space to "wander" and successfully discover the reasoning path.
Abstraction: Extracted the internal logic steps into a Composite Node, creating a hierarchical proof structure.
Persistence: Forced a sync to disk with diagram_save and verified it with the diagram_list_saved tool.
Proof: Exported a structural trace confirming the transformation history.
The system handled everything—from the sub-diagram creation to the atomic disk persistence—while maintaining a valid logical structure.

Please see docs/demo_results.md for the full trace and proof.
