"""
Persistence layer for cognitive diagram navigation.

Handles serialization and deserialization of diagrams to disk using JSON.
"""

import json
from pathlib import Path
from typing import List, Optional

import structlog

from .models import DerivationStep, Diagram, DiagramEdge, DiagramNode

logger = structlog.get_logger(__name__)


class StorageManager:
    """
    Manages diagram persistence on disk.
    """

    def __init__(self, base_dir: Optional[str] = None) -> None:
        """
        Initialize the storage manager.

        Args:
            base_dir: Base directory for diagram storage.
                      Defaults to ~/.cognitive_diagram_nav/diagrams
        """
        if base_dir:
            self.base_dir = Path(base_dir)
        else:
            self.base_dir = Path.home() / ".cognitive_diagram_nav" / "diagrams"

        self.base_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Initialized storage manager", base_dir=str(self.base_dir))

    def _get_path(self, diagram_id: str) -> Path:
        """Get the file path for a diagram ID."""
        return self.base_dir / f"{diagram_id}.json"

    def save_diagram(self, diagram: Diagram) -> bool:
        """
        Save a diagram to disk.

        Args:
            diagram: The diagram object to save.

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            path = self._get_path(diagram.diagram_id)

            # Serialize diagram structure
            data = {
                "diagram_id": diagram.diagram_id,
                "nodes": {
                    nid: {
                        "id": node.id,
                        "label": node.label,
                        "node_type": node.node_type,
                        "metadata": node.metadata,
                        "embedding": node.embedding,
                        "sub_diagram_id": node.sub_diagram_id,
                        "visited": node.visited,
                        "depth": node.depth,
                    }
                    for nid, node in diagram.nodes.items()
                },
                "edges": [
                    {
                        "source": edge.source,
                        "target": edge.target,
                        "label": edge.label,
                        "properties": edge.properties,
                        "weight": edge.weight,
                    }
                    for edge in diagram.edges
                ],
                "transformations": [
                    {
                        "rule_name": step.rule_name,
                        "match_mapping": step.match_mapping,
                        "timestamp": step.timestamp,
                        "description": step.description,
                        "diagram_before": step.diagram_before,
                        "diagram_after": step.diagram_after,
                    }
                    for step in diagram.transformations
                ],
            }

            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            logger.info("Saved diagram to disk", diagram_id=diagram.diagram_id, path=str(path))
            return True
        except (OSError, TypeError, ValueError) as e:
            logger.error("Failed to save diagram", diagram_id=diagram.diagram_id, error=str(e))
            return False

    def load_diagram(self, diagram_id: str) -> Optional[Diagram]:
        """
        Load a diagram from disk.

        Args:
            diagram_id: The ID of the diagram to load.

        Returns:
            Optional[Diagram]: The loaded diagram or None if not found or error.
        """
        path = self._get_path(diagram_id)
        if not path.exists():
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            nodes = {
                nid: DiagramNode(
                    id=ndata["id"],
                    label=ndata["label"],
                    node_type=ndata["node_type"],
                    metadata=ndata.get("metadata", {}),
                    embedding=ndata.get("embedding"),
                    sub_diagram_id=ndata.get("sub_diagram_id"),
                    visited=ndata.get("visited", False),
                    depth=ndata.get("depth", 0),
                )
                for nid, ndata in data["nodes"].items()
            }

            edges = [
                DiagramEdge(
                    source=edata["source"],
                    target=edata["target"],
                    label=edata["label"],
                    properties=edata.get("properties", {}),
                    weight=edata.get("weight", 1.0),
                )
                for edata in data["edges"]
            ]

            transformations = [
                DerivationStep(
                    rule_name=sdata["rule_name"],
                    match_mapping=sdata["match_mapping"],
                    timestamp=sdata["timestamp"],
                    description=sdata.get("description"),
                    diagram_before=sdata.get("diagram_before"),
                    diagram_after=sdata.get("diagram_after"),
                )
                for sdata in data.get("transformations", [])
            ]

            diagram = Diagram(
                diagram_id=data["diagram_id"],
                nodes=nodes,
                edges=edges,
            )
            diagram.transformations = transformations

            logger.info("Loaded diagram from disk", diagram_id=diagram_id)
            return diagram
        except (OSError, json.JSONDecodeError, KeyError) as e:
            logger.error("Failed to load diagram", diagram_id=diagram_id, error=str(e))
            return None

    def delete_diagram(self, diagram_id: str) -> bool:
        """
        Delete a diagram from disk.

        Args:
            diagram_id: The ID of the diagram to delete.

        Returns:
            bool: True if deleted or didn't exist, False on error.
        """
        path = self._get_path(diagram_id)
        if not path.exists():
            return True

        try:
            path.unlink()
            logger.info("Deleted diagram from disk", diagram_id=diagram_id)
            return True
        except OSError as e:
            logger.error("Failed to delete diagram", diagram_id=diagram_id, error=str(e))
            return False

    def list_diagrams(self) -> List[str]:
        """
        List all diagrams stored on disk.

        Returns:
            List[str]: List of diagram IDs.
        """
        try:
            return [f.stem for f in self.base_dir.glob("*.json")]
        except OSError as e:
            logger.error("Failed to list diagrams", error=str(e))
            return []
