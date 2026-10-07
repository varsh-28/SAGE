"""SPARQL query templates over the OpsGraph RDF graph.

Entity ids (e.g. INC-0042, payment-service) are validated against a strict pattern before being
substituted into a query, so user input can never inject SPARQL.
"""
from __future__ import annotations

import re

from rdflib import Graph

from .config import DATA, OPS

_ID = re.compile(r"^[A-Za-z0-9_\-]+$")
PREFIXES = f"PREFIX ops: <{OPS}>\nPREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"


def _iri(entity_id: str) -> str:
    if not _ID.match(entity_id):
        raise ValueError(f"invalid entity id: {entity_id!r}")
    return f"<{DATA}{entity_id}>"


def _local(term) -> str:
    return str(term).rsplit("/", 1)[-1]


def _run(g: Graph, query: str) -> list[str]:
    return sorted({_local(row[0]) for row in g.query(PREFIXES + query)})


def service_of(g: Graph, inc: str) -> list[str]:
    return _run(g, f"SELECT ?s WHERE {{ {_iri(inc)} ops:affectsService ?s }}")


def root_cause_of(g: Graph, inc: str) -> list[str]:
    return _run(g, f"SELECT ?rc WHERE {{ {_iri(inc)} ops:hasRootCause ?rc }}")


def runbook_for(g: Graph, inc: str) -> list[str]:
    return _run(g, f"SELECT ?rb WHERE {{ {_iri(inc)} ops:hasRootCause ?rc . ?rc ops:resolvedBy ?rb }}")


def same_root_cause(g: Graph, inc: str) -> list[str]:
    return _run(g, f"""
        SELECT DISTINCT ?other WHERE {{
            {_iri(inc)} ops:hasRootCause ?rc .
            ?other ops:hasRootCause ?rc .
            FILTER(?other != {_iri(inc)})
        }}""")


def dependents(g: Graph, svc: str) -> list[str]:
    """Services that directly depend on `svc`."""
    return _run(g, f"SELECT DISTINCT ?d WHERE {{ ?d ops:dependsOn {_iri(svc)} }}")


def dependencies(g: Graph, svc: str) -> list[str]:
    """Services that `svc` directly depends on."""
    return _run(g, f"SELECT DISTINCT ?d WHERE {{ {_iri(svc)} ops:dependsOn ?d }}")


def dependent_incidents(g: Graph, svc: str) -> list[str]:
    """Incidents that hit any service directly depending on `svc`."""
    return _run(g, f"""
        SELECT DISTINCT ?i WHERE {{
            ?d ops:dependsOn {_iri(svc)} .
            ?i ops:affectsService ?d .
        }}""")


def incident_card(g: Graph, inc: str) -> dict:
    """Everything one hop away from an incident, for context assembly."""
    rows = list(g.query(PREFIXES + f"""
        SELECT ?svc ?env ?rcl ?rbl ?rc ?rb WHERE {{
            {_iri(inc)} ops:affectsService ?svc ;
                        ops:hasEnvironment ?e ;
                        ops:hasRootCause ?rc .
            ?e rdfs:label ?env .
            ?rc rdfs:label ?rcl ; ops:resolvedBy ?rb .
            ?rb rdfs:label ?rbl .
        }}"""))
    if not rows:
        return {}
    r = rows[0]
    return {"incident": inc, "service": _local(r.svc), "environment": str(r.env),
            "root_cause": _local(r.rc), "root_cause_label": str(r.rcl),
            "runbook": _local(r.rb), "runbook_title": str(r.rbl)}
