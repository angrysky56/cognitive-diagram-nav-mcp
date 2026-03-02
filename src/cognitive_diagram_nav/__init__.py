"""
Cognitive Diagram Navigation MCP Server

An MCP server implementing diagrammatic reasoning with memory-augmented spatial navigation,
combining Quantomatic-inspired graph rewriting with hippocampal-inspired place cell encoding
for structured chain-of-thought reasoning.
"""

__version__ = "0.1.0"
__author__ = "Ty"

from .models import Diagram, DiagramEdge, DiagramNode, Pattern
from .graph_engine import GraphEngine, NavigationMemory

__all__ = [
    "Diagram",
    "DiagramNode",
    "DiagramEdge",
    "Pattern",
    "GraphEngine",
    "NavigationMemory",
]
