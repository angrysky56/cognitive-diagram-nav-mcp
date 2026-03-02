import pytest

from cognitive_diagram_nav.graph_engine import GraphEngine


@pytest.fixture
def engine() -> GraphEngine:
    return GraphEngine()


def test_proof_export_trace(engine: GraphEngine) -> None:
    # Setup diagram A -> B
    nodes = [
        {"id": "n1", "label": "A", "type": "operation"},
        {"id": "n2", "label": "B", "type": "operation"},
    ]
    edges = [{"source": "n1", "target": "n2", "label": "edge"}]
    diagram_id = engine.create_diagram(nodes, edges)

    # Apply a rule (Rename B to C)
    rule_spec = {
        "rule_name": "Rename B",
        "lhs": {"nodes": {"p_b": {"label": "B", "type": "operation"}}, "edges": []},
        "rhs": {"nodes": {"p_b": {"label": "C", "type": "operation"}}, "edges": []},
    }

    match = engine.pattern_match(diagram_id, rule_spec["lhs"])
    engine.apply_rewrite_rule(diagram_id, rule_spec, match["matches"][0])

    # Check transformations history
    diagram = engine.get_diagram(diagram_id)
    assert len(diagram.transformations) == 1
    step = diagram.transformations[0]
    assert step.rule_name == "Rename B"
    assert "n2" in step.match_mapping.values()
