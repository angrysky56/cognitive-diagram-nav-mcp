# Cognitive Diagram Navigation MCP - Quick Start Guide

## What You're Building

An **MCP (Model Context Protocol) server** that enables Claude and other LLMs to reason through:

- **Diagrammatic reasoning**: Visual/structural reasoning using graph transformations
- **Spatial navigation**: Memory-augmented exploration of reasoning spaces
- **Formal proofs**: Chain-of-thought reasoning with verifiable steps
- **Pattern matching**: Locate and apply transformations to diagrams

This bridges three research domains:
1. **Quantomatic** (diagrammatic proof assistant)
2. **Cognitive science** (hippocampal place cells, spatial memory)
3. **LLM reasoning** (chain-of-thought, structured logic)

## Project Structure

```
cognitive-diagram-nav-mcp/
├── src/cognitive_diagram_nav/
│   ├── __init__.py           # Package initialization
│   ├── models.py             # Data structures (Diagram, Pattern, etc.)
│   ├── graph_engine.py       # Core reasoning engine
│   └── server.py             # MCP FastMCP implementation
├── pyproject.toml            # Project config (uv managed)
├── README.md                 # Full documentation
├── examples.py               # Runnable examples & tests
└── QUICK_START.md           # This file
```

## Installation Steps

### 1. Prerequisites
```bash
# Ensure Python 3.12+ installed
python --version  # Should be 3.12.0+

# Install uv (recommended package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh
# Or: pip install uv
```

### 2. Navigate to Project
```bash
cd /home/ty/Repositories/ai_workspace/cognitive-diagram-nav-mcp
```

### 3. Create Virtual Environment
```bash
# Using uv (recommended)
uv venv

# Activate it
source .venv/bin/activate  # Linux/Mac
# OR
.venv\Scripts\activate     # Windows
```

### 4. Install Dependencies
```bash
# Install with dev dependencies for testing
uv pip install -e ".[dev]"

# Or minimal installation (just MCP)
uv pip install -e .
```

## Running Examples

Test the core functionality:

```bash
# Run example tests and demonstrations
python examples.py
```

Expected output:
```
============================================================
Cognitive Diagram Navigation MCP - Example Tests
============================================================

=== Test 1: Basic Diagram Creation ===
✓ Created diagram abc123...
  Nodes: 4, Edges: 3
  Valid: True

[... more tests ...]

Results: 6 passed, 0 failed
```

## Starting the MCP Server

### Option A: Direct Execution
```bash
cognitive-diagram-nav
```

The server will:
- Initialize FastMCP
- Load the GraphEngine
- Start listening on stdio (default)
- Be ready for MCP client connections

### Option B: Using uv run
```bash
uv run cognitive-diagram-nav
```

### Testing the Server

In a separate terminal:
```bash
# You can test with the MCP Inspector if available
# Or connect with Claude Desktop once configured
```

## Integrating with Claude Desktop

To use this MCP server with Claude Desktop:

### 1. Find Your Config File
- **Linux/Mac**: `~/.config/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

### 2. Add Server Configuration
```json
{
  "mcpServers": {
    "cognitive-diagram-nav": {
      "command": "uv",
      "args": [
        "run",
        "cognitive-diagram-nav"
      ]
    }
  }
}
```

**Important**: Replace the path with the actual path on your system.

### 3. Restart Claude Desktop

Claude will now have access to all MCP tools:
- `diagram_create`: Build reasoning diagrams
- `diagram_load`: Load existing diagrams
- `navigate_breadth_first`: Explore structure
- `navigate_guided`: Find optimal paths
- `analyze_reachability`: Understand connectivity
- `pattern_match`: Locate patterns
- `compute_metrics`: Analyze structure

## Using the MCP Tools

Once integrated with Claude, you can use prompts like:

### Example 1: Create and Explore
```
"Create a diagram representing a logical proof with:
- Premises as input terminals
- Logical operations in the middle
- Conclusion as output

Then explore it breadth-first from the premises."
```

### Example 2: Find Reasoning Paths
```
"In this mathematical reasoning diagram,
find the shortest path from the base axioms to the theorem,
using guided navigation."
```

### Example 3: Pattern Detection
```
"Search for any repeated logical patterns in this diagram
that could indicate opportunities for simplification or proof reuse."
```

## Development Workflow

### Code Quality

```bash
# Format code
uv run black src tests

# Lint
uv run ruff check src tests

# Type checking
uv run mypy src

# All at once
uv run black src && uv run ruff check src && uv run mypy src
```

### Testing

```bash
# Run all tests
uv run pytest

# With coverage
uv run pytest --cov=src/cognitive_diagram_nav

# Specific test file
uv run pytest tests/test_models.py -v
```

### Adding Tests

Create files in `tests/` directory following pattern:
```python
# tests/test_my_feature.py
import pytest
from cognitive_diagram_nav.graph_engine import GraphEngine

def test_my_feature():
    engine = GraphEngine()
    # your test here
    assert True
```

Then run: `uv run pytest tests/test_my_feature.py`

## Key Components Explained

### Models (`models.py`)
- **Diagram**: Complete reasoning graph
- **DiagramNode**: Individual reasoning element
- **DiagramEdge**: Connections between nodes
- **Pattern**: Templates for matching structures
- **NavigationMemory**: Tracks exploration state

### GraphEngine (`graph_engine.py`)
- Stores and manages diagrams
- Implements BFS and guided navigation
- Pattern matching algorithm
- Metric computation
- Builds NetworkX graphs for efficiency

### MCP Server (`server.py`)
- FastMCP-based implementation
- Exposes tools as MCP interface
- Tools are decorated Python functions
- Automatic JSON serialization
- Error handling and logging

## Architecture Visualization

```
User (Claude)
     ↓
   MCP Client
     ↓
   JSON-RPC (stdio)
     ↓
┌─────────────────┐
│  FastMCP Server │
├─────────────────┤
│    Tools API    │ ← MCP Tools (diagram_create, navigate_guided, etc.)
├─────────────────┤
│  GraphEngine    │ ← Core reasoning logic
├─────────────────┤
│   Models        │ ← Data structures
├─────────────────┤
│  NetworkX       │ ← Graph algorithms
└─────────────────┘
```

## Common Tasks

### Add a New Tool

1. Write the implementation in `GraphEngine`
2. Add `@server.tool()` decorated function in `server.py`
3. Add tests in `tests/`
4. Update README documentation

### Debug an Issue

1. Check logs: Server prints to stderr
2. Test independently: Use `examples.py`
3. Verify diagram structure: Use `diagram_load`
4. Check metrics: Use `compute_metrics` to understand structure

### Optimize Performance

1. Use `compute_metrics` to find bottlenecks
2. NetworkX graph is cached automatically
3. Consider max_diagrams setting in GraphEngine
4. Profile with: `uv run py-spy`

## Troubleshooting

### "Module not found" error
```bash
# Ensure you're in the venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Reinstall
uv pip install -e ".[dev]"
```

### MCP not connecting to Claude
```bash
# Check config file exists and is valid JSON
cat ~/.config/Claude/claude_desktop_config.json

# Test server directly
python src/cognitive_diagram_nav/server.py

# Restart Claude Desktop completely
```

### Tests failing
```bash
# Run with verbose output
uv run pytest examples.py -v

# Check Python version
python --version  # Must be 3.12+

# Reinstall dependencies
uv pip install --force-reinstall -e ".[dev]"
```

## Next Steps

1. **Run examples.py** to verify installation
2. **Read README.md** for full documentation
3. **Integrate with Claude** following the config steps
4. **Explore tools** by asking Claude questions
5. **Build custom diagrams** for your use case
6. **Extend functionality** by adding new tools

## Resources

- **MCP Spec**: https://modelcontextprotocol.io
- **FastMCP**: Official Python MCP framework
- **NetworkX**: Graph algorithms library
- **Quantomatic**: Diagrammatic reasoning inspiration

## Support

For issues or questions:
1. Check the full README.md
2. Review examples.py for usage patterns
3. Enable debug logging in server.py
4. Check MCP server logs for errors

---

**Status**: Alpha (v0.1.0)
**Last Updated**: 2025-02-25
**Ready for**: Learning, experimentation, integration with Claude
