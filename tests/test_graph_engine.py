import pytest
from cognitive_diagram_nav.graph_engine import GraphEngine

@pytest.fixture
def engine():
    return GraphEngine()

def test_diagram_creation(engine):
    nodes = [
        {'id': 'n1', 'label': 'Node 1', 'type': 'operation'},
        {'id': 'n2', 'label': 'Node 2', 'type': 'terminal'}
    ]
    edges = [
        {'source': 'n1', 'target': 'n2', 'label': 'edge1'}
    ]
    diagram_id = engine.create_diagram(nodes, edges)
    diagram = engine.get_diagram(diagram_id)
    assert diagram is not None
    assert diagram.num_nodes() == 2
    assert diagram.num_edges() == 1

def test_pattern_match_simple(engine):
    nodes = [
        {'id': 'n1', 'label': 'A', 'type': 'operation'},
        {'id': 'n2', 'label': 'B', 'type': 'operation'},
        {'id': 'n3', 'label': 'C', 'type': 'terminal'}
    ]
    edges = [
        {'source': 'n1', 'target': 'n2', 'label': 'to_b'},
        {'source': 'n2', 'target': 'n3', 'label': 'to_c'}
    ]
    diagram_id = engine.create_diagram(nodes, edges)

    pattern = {
        'nodes': {
            'p1': {'type': 'operation'},
            'p2': {'type': 'terminal'}
        },
        'edges': [
            ('p1', 'p2', {})
        ]
    }

    result = engine.pattern_match(diagram_id, pattern)
    # n2 -> n3 matches p1 -> p2
    assert result['num_matches'] > 0

    # Check if specifically n2 -> n3 is found
    found = False
    for match in result['matches']:
        if match.get('p1') == 'n2' and match.get('p2') == 'n3':
            found = True
            break
    assert found

def test_bfs_navigation(engine):
    nodes = [
        {'id': 'n1', 'label': 'Root', 'type': 'operation'},
        {'id': 'n2', 'label': 'L1', 'type': 'operation'},
        {'id': 'n3', 'label': 'L1', 'type': 'operation'},
        {'id': 'n4', 'label': 'L2', 'type': 'terminal'}
    ]
    edges = [
        {'source': 'n1', 'target': 'n2', 'label': 'e1'},
        {'source': 'n1', 'target': 'n3', 'label': 'e2'},
        {'source': 'n2', 'target': 'n4', 'label': 'e3'}
    ]
    diagram_id = engine.create_diagram(nodes, edges)

    result = engine.navigate_breadth_first(diagram_id, 'n1', max_depth=2)
    assert result['total_explored'] == 4
    ids = [n['id'] for n in result['explored_nodes']]
    assert 'n1' in ids
    assert 'n2' in ids
    assert 'n3' in ids
    assert 'n4' in ids

def test_semantic_search(engine):
    nodes = [
        {'id': 'n1', 'label': 'A', 'type': 'operation', 'embedding': [1.0, 0.0, 0.0]},
        {'id': 'n2', 'label': 'B', 'type': 'operation', 'embedding': [0.9, 0.1, 0.0]},
        {'id': 'n3', 'label': 'C', 'type': 'operation', 'embedding': [0.0, 1.0, 0.0]}
    ]
    edges = []
    diagram_id = engine.create_diagram(nodes, edges)

    # Search for something close to [1, 0, 0]
    result = engine.node_semantic_search(diagram_id, [1.0, 0.0, 0.0], top_k=2)
    assert len(result['matches']) == 2
    assert result['matches'][0]['id'] == 'n1' # Exact match
    assert result['matches'][1]['id'] == 'n2' # Close match

def test_semantic_guided_navigation(engine):
    # n1 -> n2 -> n4 (path 1)
    # n1 -> n3 -> n4 (path 2)
    # Goal is n4 [0, 1]. n2 is [0.1, 0.9], n3 is [0.9, 0.1]
    # Semantic search should strongly prefer n2.
    nodes = [
        {'id': 'n1', 'label': 'Start', 'type': 'operation', 'embedding': [0.0, 0.0]},
        {'id': 'n2', 'label': 'Good Path', 'type': 'operation', 'embedding': [0.1, 0.9]},
        {'id': 'n3', 'label': 'Bad Path', 'type': 'operation', 'embedding': [0.9, 0.1]},
        {'id': 'n4', 'label': 'Goal', 'type': 'terminal', 'embedding': [0.0, 1.0]}
    ]
    edges = [
        {'source': 'n1', 'target': 'n2', 'label': 'e1'},
        {'source': 'n1', 'target': 'n3', 'label': 'e2'},
        {'source': 'n2', 'target': 'n4', 'label': 'e3'},
        {'source': 'n3', 'target': 'n4', 'label': 'e4'}
    ]
    diagram_id = engine.create_diagram(nodes, edges)

    result = engine.navigate_guided(diagram_id, 'n1', 'n4', heuristic='semantic_similarity')

    assert result['found'] is True
    # In A*, the path should match the shortest valid path, prioritizing nodes with lower heuristic.
    # While both paths have 2 cost, A* expansion would favor n2.
    # We just check it found it and heuristic used is recorded.
    assert result['heuristic_used'] == 'semantic_similarity'
    assert result['path'][-1] == 'n4'
