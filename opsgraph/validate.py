"""SHACL validation of the graph against ontology/shapes.ttl."""
from __future__ import annotations

from pyshacl import validate
from rdflib import Graph

from .config import SHAPES_FILE


def validate_graph(data_graph: Graph) -> tuple[bool, str]:
    shapes = Graph().parse(SHAPES_FILE, format="turtle")
    conforms, _report_graph, report_text = validate(
        data_graph, shacl_graph=shapes, inference="none", abort_on_first=False)
    return bool(conforms), report_text


if __name__ == "__main__":
    from .graph_builder import build_and_save

    ok, text = validate_graph(build_and_save())
    print("CONFORMS" if ok else text)
