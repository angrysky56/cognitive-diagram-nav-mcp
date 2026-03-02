import shutil
import tempfile
from pathlib import Path
from typing import Any, Iterator, Optional

import pytest

from cognitive_diagram_nav.graph_engine import GraphEngine


@pytest.fixture
def temp_storage() -> Iterator[str]:
    """Create a temporary directory for storage tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def engine(temp_storage: str) -> GraphEngine:
    """Initialize GraphEngine with temporary storage and low max_diagrams for LRU test."""
    return GraphEngine(max_diagrams=2, storage_dir=temp_storage)


def test_diagram_persistence_on_creation(engine: GraphEngine, temp_storage: str) -> None:
    """Verify that creating a diagram saves it to disk."""
    nodes: list[dict[str, Any]] = [{"id": "n1", "label": "Start", "type": "operation"}]
    edges: list[dict[str, Any]] = []
    diagram_id = engine.create_diagram(nodes, edges)

    # Check disk
    path = Path(temp_storage) / f"{diagram_id}.json"
    assert path.exists()


def test_lru_eviction_and_disk_recovery(engine: GraphEngine, temp_storage: str) -> None:
    """Verify LRU eviction removes from memory but recovery loads from disk."""
    # Create 3 diagrams with max_diagrams=2
    d1 = engine.create_diagram([{"id": "n1", "label": "D1", "type": "operation"}], [])
    d2 = engine.create_diagram([{"id": "n2", "label": "D2", "type": "operation"}], [])

    # d1 and d2 are in memory. d1 is LRU.
    assert d1 in engine.diagrams
    assert d2 in engine.diagrams

    # Create d3, should evict d1
    d3 = engine.create_diagram([{"id": "n3", "label": "D3", "type": "operation"}], [])

    assert d1 not in engine.diagrams
    assert d2 in engine.diagrams
    assert d3 in engine.diagrams

    # Verify d1 is still on disk
    assert (Path(temp_storage) / f"{d1}.json").exists()

    # Recover d1 from disk
    recovered_d1 = engine.get_diagram(d1)
    assert recovered_d1 is not None
    assert recovered_d1.diagram_id == d1
    assert "n1" in recovered_d1.nodes

    # d1 should be back in memory, and d2 should now be LRU
    assert d1 in engine.diagrams

    # Access d3 to make it most recent
    engine.get_diagram(d3)

    # Create d4, should evict d2 (since it was LRU before d1 was re-added or accessed)
    # Wait, get_diagram(d1) made d1 most recent. d2 was LRU.
    d4 = engine.create_diagram([{"id": "n4", "label": "D4", "type": "operation"}], [])
    assert d2 not in engine.diagrams
    assert d4 in engine.diagrams


def test_explicit_save_and_delete(engine: GraphEngine, temp_storage: str) -> None:
    """Verify explicit save and delete operations."""
    nodes = [{"id": "n1", "label": "Test", "type": "operation"}]
    d_id = engine.create_diagram(nodes, [])

    # Delete from memory and disk
    success = engine.delete_diagram(d_id)
    assert success is True
    assert d_id not in engine.diagrams
    assert not (Path(temp_storage) / f"{d_id}.json").exists()


def test_list_saved_diagrams(engine: GraphEngine, temp_storage: str) -> None:
    """Verify listing saved diagrams."""
    d1 = engine.create_diagram([{"id": "n1", "label": "D1", "type": "operation"}], [])
    d2 = engine.create_diagram([{"id": "n2", "label": "D2", "type": "operation"}], [])

    saved_ids = engine.list_saved_diagrams()
    assert d1 in saved_ids
    assert d2 in saved_ids
    assert len(saved_ids) == 2
