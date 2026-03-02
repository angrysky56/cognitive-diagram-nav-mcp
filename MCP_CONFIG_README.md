# Claude Desktop Configuration

This directory contains configuration files for integrating the Cognitive Diagram Navigation MCP server with Claude Desktop.

## Setup Instructions

### Option 1: Auto-Merge (Recommended)

1. Copy the contents of `claude_desktop_config_example.json`
2. Locate your Claude Desktop config file:
   - **Linux/Mac**: `~/.config/Claude/claude_desktop_config.json`
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
3. Open it in a text editor
4. Merge the `mcpServers` section from the example into your existing config
5. Save and restart Claude Desktop

### Option 2: Replace Entire Config

If you don't have other MCP servers configured:

```bash
# Linux/Mac
cp claude_desktop_config_example.json ~/.config/Claude/claude_desktop_config.json

# Windows (in PowerShell)
Copy-Item claude_desktop_config_example.json $env:APPDATA\Claude\claude_desktop_config.json
```

### Verify Configuration

After restart, Claude Desktop should show the MCP connection indicator. You can test by asking Claude:

```
"Create a diagram with 3 nodes and 2 edges connecting them"
```

## Configuration Details

The config tells Claude Desktop to:
- Run: `uv run`
- With MCP support: `--with mcp`
- Execute: `server.py` from the cognitive-diagram-nav-mcp package

## Available Tools

Once connected, Claude will have access to:

1. **diagram_create** - Create new reasoning diagrams
2. **diagram_load** - Load existing diagrams
3. **navigate_breadth_first** - Explore diagram structure
4. **navigate_guided** - Find optimal paths
5. **analyze_reachability** - Understand connectivity
6. **pattern_match** - Locate patterns in diagrams
7. **compute_metrics** - Analyze structure properties
8. **server_info** - Get server status

## Troubleshooting

**MCP not connecting?**
- Verify the file path is correct
- Ensure `uv` is installed: `uv --version`
- Check Claude Desktop logs
- Restart Claude Desktop completely

**Path wrong for your system?**
Update the path in the config to match your installation:
```json
"args": [
  "run",
  "--with",
  "mcp",
  "/path/to/your/cognitive-diagram-nav-mcp/src/cognitive_diagram_nav/server.py"
]
```

## Updating

To update the server:
```bash
cd /home/ty/Repositories/ai_workspace/cognitive-diagram-nav-mcp
git pull  # or manually update files
```

No Claude Desktop config changes needed - it will use the updated code.
