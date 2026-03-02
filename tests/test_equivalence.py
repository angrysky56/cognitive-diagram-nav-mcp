import pytest

from cognitive_diagram_nav.graph_engine import GraphEngine


@pytest.fixture
def engine() -> GraphEngine:
    return GraphEngine()

def test_check_diagram_equivalence(engine: GraphEngine) -> None:
    # Diagram 1: A -> B
    nodes1 = [
        {'id': 'n1', 'label': 'A', 'type': 'operation'},
        {'id': 'n2', 'label': 'B', 'type': 'operation'}
    ]
    edges1 = [{'source': 'n1', 'target': 'n2', 'label': 'edge'}]
    id1 = engine.create_diagram(nodes1, edges1)

    # Diagram 2: X -> Y (same structure, different IDs, same labels/types)
    nodes2 = [
        {'id': 'x', 'label': 'A', 'type': 'operation'},
        {'id': 'y', 'label': 'B', 'type': 'operation'}
    ]
    edges2 = [{'source': 'x', 'target': 'y', 'label': 'edge'}]
    id2 = engine.create_diagram(nodes2, edges2)

    # Diagram 3: A -> C (different label)
    nodes3 = [
        {'id': 'n1', 'label': 'A', 'type': 'operation'},
        {'id': 'n2', 'label': 'C', 'type': 'operation'}
    ]
    edges3 = [{'source': 'n1', 'target': 'n2', 'label': 'edge'}]
    id3 = engine.create_diagram(nodes3, edges3)

    assert engine.check_diagram_equivalence(id1, id2) is True
    assert engine.check_diagram_equivalence(id1, id3) is False

def test_explore_equivalent_states(engine: GraphEngine) -> None:
    # A -> B
    nodes = [
        {'id': 'n1', 'label': 'A', 'type': 'operation'},
        {'id': 'n2', 'label': 'B', 'type': 'operation'}
    ]
    edges = [{'source': 'n1', 'target': 'n2', 'label': 'to_b'}]
    diagram_id = engine.create_diagram(nodes, edges)

    # Rule: Rename A to C
    rule_spec = {
        'rule_name': 'Rename A',
        'lhs': {
            'nodes': {'p_a': {'label': 'A', 'type': 'operation'}},
            'edges': []
        },
        'rhs': {
            'nodes': {'p_a': {'label': 'C', 'type': 'operation'}},
            'edges': []
        }
    }

    result = engine.explore_equivalent_states(diagram_id, [rule_spec], max_depth=1)

    # Should find 2 states: (A->B) and (C->B)
    assert result['num_states_found'] == 2
    assert len(result['meta_edges']) == 1
