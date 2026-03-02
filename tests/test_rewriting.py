import pytest
from cognitive_diagram_nav.graph_engine import GraphEngine

@pytest.fixture
def engine():
    return GraphEngine()

def test_simple_dpo_rewrite(engine):
    # Initial diagram: A -> B -> C
    nodes = [
        {'id': 'n1', 'label': 'A', 'type': 'operation'},
        {'id': 'n2', 'label': 'B', 'type': 'operation'},
        {'id': 'n3', 'label': 'C', 'type': 'operation'}
    ]
    edges = [
        {'source': 'n1', 'target': 'n2', 'label': 'to_b'},
        {'source': 'n2', 'target': 'n3', 'label': 'to_c'}
    ]
    diagram_id = engine.create_diagram(nodes, edges)

    # Rule: B -> C is rewritten to B -> D
    # LHS: B -> C
    # RHS: B -> D
    # Boundary: B
    rule_spec = {
        'rule_name': 'Rewrite C to D',
        'lhs': {
            'nodes': {
                'p_b': {'type': 'operation', 'label': 'B'},
                'p_c': {'type': 'operation', 'label': 'C'}
            },
            'edges': [
                ('p_b', 'p_c', {})
            ]
        },
        'rhs': {
            'nodes': {
                'p_b': {'type': 'operation', 'label': 'B'},
                'p_new': {'type': 'operation', 'label': 'D'}
            },
            'edges': [
                ('p_b', 'p_new', {'label': 'to_d'})
            ]
        }
    }

    # Match LHS in diagram
    match_result = engine.pattern_match(diagram_id, rule_spec['lhs'])
    assert match_result['num_matches'] == 1
    mapping = match_result['matches'][0]

    # mapping should logically be: {'p_b': 'n2', 'p_c': 'n3'}
    # Apply rewrite
    rewrite_result = engine.apply_rewrite_rule(diagram_id, rule_spec, mapping)

    assert rewrite_result['success'] is True
    assert rewrite_result['nodes_removed'] == 1
    assert rewrite_result['nodes_added'] == 1

    # Verify diagram state
    diagram = engine.get_diagram(diagram_id)
    # n3 (C) should be gone, new node D should be there
    assert 'n3' not in diagram.nodes

    # Should have A, B, and the new D
    assert diagram.num_nodes() == 3
    # n1 -> n2, and n2 -> fresh_id
    assert diagram.num_edges() == 2

    # Check that A -> B is still intact (gluing held)
    assert any(e.source == 'n1' and e.target == 'n2' for e in diagram.edges)

def test_dangling_condition_violation(engine):
    # Diagram: A -> B -> C
    nodes = [
        {'id': 'n1', 'label': 'A', 'type': 'operation'},
        {'id': 'n2', 'label': 'B', 'type': 'operation'},
        {'id': 'n3', 'label': 'C', 'type': 'operation'}
    ]
    edges = [
        {'source': 'n1', 'target': 'n2', 'label': 'to_b'},
        {'source': 'n2', 'target': 'n3', 'label': 'to_c'}
    ]
    diagram_id = engine.create_diagram(nodes, edges)

    # Rule: Replace B with D.
    # LHS only specifies B.
    # Because A -> B and B -> C exist in the diagram but NOT in LHS, deleting B violates dangling condition.
    rule_spec = {
        'rule_name': 'Bad Deletion',
        'lhs': {
            'nodes': {
                'p_b': {'type': 'operation', 'label': 'B'}
            },
            'edges': []
        },
        'rhs': {
            'nodes': {
                'p_d': {'type': 'operation', 'label': 'D'}
            },
            'edges': []
        }
    }

    match_result = engine.pattern_match(diagram_id, rule_spec['lhs'])
    assert match_result['num_matches'] == 1
    mapping = match_result['matches'][0]

    with pytest.raises(ValueError, match="Dangling condition violation"):
        engine.apply_rewrite_rule(diagram_id, rule_spec, mapping)
