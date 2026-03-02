import pytest
from cognitive_diagram_nav.graph_engine import GraphEngine

@pytest.fixture
def engine():
    return GraphEngine()

def test_explore_reasoning_space(engine):
    # Create simple diagram: A -> B, A -> C, B -> D, C -> D
    nodes = [
        {'id': 'A', 'label': 'A', 'type': 'operation'},
        {'id': 'B', 'label': 'B', 'type': 'operation'},
        {'id': 'C', 'label': 'C', 'type': 'operation'},
        {'id': 'D', 'label': 'D', 'type': 'operation'}
    ]
    edges = [
        {'source': 'A', 'target': 'B', 'label': 'to_b'},
        {'source': 'A', 'target': 'C', 'label': 'to_c'},
        {'source': 'B', 'target': 'D', 'label': 'b_to_d'},
        {'source': 'C', 'target': 'D', 'label': 'c_to_d'}
    ]
    diagram_id = engine.create_diagram(nodes, edges)

    # First exploration (greedy)
    result1 = engine.explore_reasoning_space(diagram_id, 'A', steps=2, temperature=0.0)
    assert result1['steps_taken'] == 2
    path1 = result1['path']
    assert path1[0] == 'A'
    assert path1[1] in ('B', 'C')
    assert path1[2] == 'D'

    # B or C was visited. Let's force a second exploration and verify it picks the OTHER branch
    # if temperature is 0.0, because the other branch has exploration count 0.
    # Note: 'A' has count 2 now.
    result2 = engine.explore_reasoning_space(diagram_id, 'A', steps=2, temperature=0.0)
    path2 = result2['path']

    assert path1[1] != path2[1], "Greedy exploration should prefer the unvisited branch"

    # Counts should be updated correctly
    counts = result2['exploration_counts']
    for node in path2:
        assert counts[node] >= 1

def test_dead_end_exploration(engine):
    nodes = [{'id': 'A', 'label': 'A', 'type': 'operation'}]
    diagram_id = engine.create_diagram(nodes, [])

    # Should stop cleanly at dead end A
    result = engine.explore_reasoning_space(diagram_id, 'A', steps=5)
    assert result['steps_taken'] == 0
    assert result['path'] == ['A']
