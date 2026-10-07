from rdflib import RDF, Literal, Namespace

from opsgraph.config import DATA, OPS
from opsgraph.validate import validate_graph

OPSNS, D = Namespace(OPS), Namespace(DATA)


def test_generated_graph_conforms(graph):
    ok, report = validate_graph(graph)
    assert ok, report


def test_incident_without_root_cause_is_rejected(graph):
    bad = type(graph)()
    for t in graph:
        bad.add(t)
    inc = D["INC-9999"]
    bad.add((inc, RDF.type, OPSNS.Incident))
    bad.add((inc, OPSNS.affectsService, D["payment-service"]))
    bad.add((inc, OPSNS.severity, Literal("SEV9")))  # invalid severity too
    ok, report = validate_graph(bad)
    assert not ok
    assert "RootCause" in report or "root" in report.lower()


def test_self_dependency_is_rejected(graph):
    bad = type(graph)()
    for t in graph:
        bad.add(t)
    bad.add((D["payment-service"], OPSNS.dependsOn, D["payment-service"]))
    ok, report = validate_graph(bad)
    assert not ok
    assert "depend on itself" in report
