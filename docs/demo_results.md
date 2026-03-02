# 🧪 Live Demo: Logical Reasoning & Persistence

I've executed a full reasoning cycle using the MCP tools to demonstrate the system's capabilities.

## 1. Diagram Initiation
I created a diagram representing the logical proof: **$(A \land B) \to (B \land A)$**.
- **Input**: [(A ^ B)](file:///home/ty/Repositories/ai_workspace/cognitive-diagram-nav-mcp/src/cognitive_diagram_nav/server.py#781-785)
- **Output**: [(B ^ A)](file:///home/ty/Repositories/ai_workspace/cognitive-diagram-nav-mcp/src/cognitive_diagram_nav/server.py#781-785)
- **Intermediate Nodes**: `A`, `B`
- **Diagram ID**: `50fc55f9-d1a9-41fa-bae0-da8c67260276`

## 2. Path Exploration (Curiosity Engine)
I used [explore_reasoning_space](file:///home/ty/Repositories/ai_workspace/cognitive-diagram-nav-mcp/src/cognitive_diagram_nav/graph_engine.py#1042-1115) to "wander" the graph starting from the premise. The engine successfully discovered the reasoning path:
- **Path**: `start` ($A \land B$) → `node_a` ($A$) → [end](file:///home/ty/Repositories/ai_workspace/cognitive-diagram-nav-mcp/tests/test_exploration.py#45-53) ($B \land A$)
- **Steps Taken**: 2

## 3. Structural Abstraction
To simplify the proof for a high-level observer, I extracted the intermediate logic steps (`node_a`, `node_b`) into a **Composite Node**.
- **Composite Label**: "And-Commutativity Proof Segment"
- **New Composite ID**: `271c9bf0-9b77-41d8-a594-32b19ec1c134`
- **Sub-diagram**: The engine automatically created a child diagram (`36cbcb0f-68a3-49b3-ab47-54d21db1ea76`) to hold the internal logic.

## 4. Persistent Storage
I verified the persistence layer:
- **[diagram_save](file:///home/ty/Repositories/ai_workspace/cognitive-diagram-nav-mcp/src/cognitive_diagram_nav/server.py#663-684)**: Successfully persisted the transformed diagram to disk.
- **[diagram_list_saved](file:///home/ty/Repositories/ai_workspace/cognitive-diagram-nav-mcp/src/cognitive_diagram_nav/server.py#686-704)**: Confirmed that the diagram (and its sub-diagram) are now visible to other sessions.
- **[export_proof](file:///home/ty/Repositories/ai_workspace/cognitive-diagram-nav-mcp/src/cognitive_diagram_nav/server.py#429-467)**: Generated a structural proof trace:
    1. *Extracted nodes into composite 271c9bf0-9b77-41d8-a594-32b19ec1c134 (subdiagram 36cbcb0f-68a3-49b3-ab47-54d21db1ea76)*

## 🏁 Conclusion
The system successfully handled **hierarchical reasoning**, **automated path discovery**, and **atomic disk persistence**, all while maintaining a valid logical structure.
