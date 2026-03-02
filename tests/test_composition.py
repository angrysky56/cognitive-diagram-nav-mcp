import pytest
from cognitive_diagram_nav.graph_engine import GraphEngine

@pytest.fixture
def engine():
    return GraphEngine()

def test_cyclic_reference_validation(engine):
    # Diagram A
    diagram_a_id = engine.create_diagram(
        nodes=[{'id': 'n1', 'label': 'A1', 'type': 'operation'}],
        edges=[]
    )

    # Diagram B containing A
    diagram_b_id = engine.create_diagram(
        nodes=[
            {'id': 'n2', 'label': 'B1', 'type': 'composite', 'sub_diagram_id': diagram_a_id}
        ],
        edges=[]
    )

    # Diagram C containing B (valid)
    assert engine.create_diagram(
        nodes=[
            {'id': 'n3', 'label': 'C1', 'type': 'composite', 'sub_diagram_id': diagram_b_id}
        ],
        edges=[]
    )

    # Attempt to create Diagram D containing itself
    with pytest.raises(ValueError, match="Cyclic diagram reference detected"):
        # We can't actually do this in one step unless we use a pre-existing ID,
        # but the cycle check looks at existing diagrams. Let's make diagram A point to diagram B
        # which points to diagram A. We have to do this by modifying A directly.
        diag_a = engine.get_diagram(diagram_a_id)
        diag_a.nodes['n1'].sub_diagram_id = diagram_b_id

        # Now if we create diagram E pointing to A, it should detect A -> B -> A cycle
        engine.create_diagram(
            nodes=[
                {'id': 'n4', 'label': 'E1', 'type': 'composite', 'sub_diagram_id': diagram_a_id}
            ],
            edges=[]
        )

def test_diagram_extract(engine):
    # Create simple diagram: A -> B -> C -> D
    nodes = [
        {'id': 'n1', 'label': 'A', 'type': 'operation'},
        {'id': 'n2', 'label': 'B', 'type': 'operation'},
        {'id': 'n3', 'label': 'C', 'type': 'operation'},
        {'id': 'n4', 'label': 'D', 'type': 'operation'}
    ]
    edges = [
        {'source': 'n1', 'target': 'n2', 'label': 'a_to_b'},
        {'source': 'n2', 'target': 'n3', 'label': 'b_to_c'},
        {'source': 'n3', 'target': 'n4', 'label': 'c_to_d'}
    ]
    diagram_id = engine.create_diagram(nodes, edges)

    # Extract B and C into a composite node
    result = engine.diagram_extract(diagram_id, ['n2', 'n3'], "Extracted BC")
    assert result['success'] is True

    composite_id = result['composite_node_id']
    sub_diagram_id = result['sub_diagram_id']

    diagram = engine.get_diagram(diagram_id)
    # Original diagram should now only have A, D, and composite_id
    assert 'n1' in diagram.nodes
    assert 'n4' in diagram.nodes
    assert composite_id in diagram.nodes
    assert 'n2' not in diagram.nodes
    assert 'n3' not in diagram.nodes

    # New edges should be A -> composite -> D
    assert len(diagram.edges) == 2
    edge_a_to_comp = next(e for e in diagram.edges if e.source == 'n1')
    assert edge_a_to_comp.target == composite_id
    assert edge_a_to_comp.label == 'a_to_b'

    edge_comp_to_d = next(e for e in diagram.edges if e.target == 'n4')
    assert edge_comp_to_d.source == composite_id
    assert edge_comp_to_d.label == 'c_to_d'

    # Verify subdiagram
    sub_diagram = engine.get_diagram(sub_diagram_id)
    assert 'n2' in sub_diagram.nodes
    assert 'n3' in sub_diagram.nodes
    assert len(sub_diagram.edges) == 1
    assert sub_diagram.edges[0].source == 'n2'
    assert sub_diagram.edges[0].target == 'n3'

def test_navigate_guided_expand_composites(engine):
    # Inner diagram: B -> C
    inner_id = engine.create_diagram(
        nodes=[
            {'id': 'n2', 'label': 'B', 'type': 'operation'},
            {'id': 'n3', 'label': 'C', 'type': 'operation'}
        ],
        edges=[{'source': 'n2', 'target': 'n3', 'label': 'b_to_c'}]
    )

    # Outer diagram: A -> [Inner]
    outer_id = engine.create_diagram(
        nodes=[
            {'id': 'n1', 'label': 'A', 'type': 'operation'},
            {'id': 'comp', 'label': 'Inner', 'type': 'composite', 'sub_diagram_id': inner_id}
        ],
        edges=[{'source': 'n1', 'target': 'comp', 'label': 'a_to_inner'}]
    )

    # Search from A to C without expand should fail
    with pytest.raises(ValueError):
        engine.navigate_guided(outer_id, 'n1', 'n3', expand_composites=False)

    # Search from A to C with expand should succeed
    result = engine.navigate_guided(outer_id, 'n1', 'n3', expand_composites=True)
    assert result['found'] is True
    assert result['path'] == ['n1', 'comp', 'n2', 'n3']
