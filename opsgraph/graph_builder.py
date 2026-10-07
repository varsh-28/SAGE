"""Turn the raw dataset into an RDF graph that conforms to ontology/opsgraph.ttl."""
from __future__ import annotations

import json

from rdflib import RDF, RDFS, SKOS, XSD, Graph, Literal, Namespace

from .config import DATA, GRAPH_FILE, ONTOLOGY_FILE, OPS
from .generate_data import ensure

OPSNS = Namespace(OPS)
D = Namespace(DATA)


def build_graph(ds: dict, include_ontology: bool = True) -> Graph:
    g = Graph()
    g.bind("ops", OPSNS)
    g.bind("data", D)
    g.bind("skos", SKOS)
    if include_ontology:
        g.parse(ONTOLOGY_FILE, format="turtle")

    # SKOS symptom vocabulary
    scheme = D["symptom_scheme"]
    g.add((scheme, RDF.type, SKOS.ConceptScheme))
    g.add((scheme, SKOS.prefLabel, Literal("Operational symptoms", lang="en")))
    for grp in sorted({s["group"] for s in ds["symptoms"]}):
        gid = D["grp_" + grp.lower()]
        g.add((gid, RDF.type, SKOS.Concept))
        g.add((gid, SKOS.prefLabel, Literal(grp, lang="en")))
        g.add((gid, SKOS.inScheme, scheme))
        g.add((gid, SKOS.topConceptOf, scheme))
    for s in ds["symptoms"]:
        c = D[s["id"]]
        g.add((c, RDF.type, SKOS.Concept))
        g.add((c, SKOS.prefLabel, Literal(s["label"], lang="en")))
        for a in s["alt"]:
            g.add((c, SKOS.altLabel, Literal(a, lang="en")))
        g.add((c, SKOS.inScheme, scheme))
        g.add((c, SKOS.broader, D["grp_" + s["group"].lower()]))

    for e in ds["environments"]:
        g.add((D[e["id"]], RDF.type, OPSNS.Environment))
        g.add((D[e["id"]], RDFS.label, Literal(e["name"])))

    for s in ds["services"]:
        u = D[s["id"]]
        g.add((u, RDF.type, OPSNS.Service))
        g.add((u, RDFS.label, Literal(s["name"])))
        g.add((u, OPSNS.tier, Literal(s["tier"])))
        for dep in s["depends_on"]:
            g.add((u, OPSNS.dependsOn, D[dep]))

    for r in ds["runbooks"]:
        g.add((D[r["id"]], RDF.type, OPSNS.Runbook))
        g.add((D[r["id"]], RDFS.label, Literal(r["title"])))

    for r in ds["root_causes"]:
        u = D[r["id"]]
        g.add((u, RDF.type, OPSNS.RootCause))
        g.add((u, RDFS.label, Literal(r["label"])))
        g.add((u, OPSNS.category, Literal(r["category"])))
        g.add((u, OPSNS.resolvedBy, D[r["runbook"]]))

    for d in ds["deployments"]:
        u = D[d["id"]]
        g.add((u, RDF.type, OPSNS.Deployment))
        g.add((u, OPSNS.deploymentOf, D[d["service"]]))
        g.add((u, OPSNS.deployedTo, D[d["env"]]))
        g.add((u, OPSNS.version, Literal(d["version"])))
        g.add((u, OPSNS.deployedAt, Literal(d["deployed_at"], datatype=XSD.dateTime)))

    for a in ds["alerts"]:
        g.add((D[a["id"]], RDF.type, OPSNS.Alert))
        g.add((D[a["id"]], OPSNS.alertName, Literal(a["name"])))

    for i in ds["incidents"]:
        u = D[i["id"]]
        g.add((u, RDF.type, OPSNS.Incident))
        g.add((u, OPSNS.affectsService, D[i["service"]]))
        g.add((u, OPSNS.hasEnvironment, D[i["env"]]))
        g.add((u, OPSNS.hasRootCause, D[i["root_cause"]]))
        g.add((u, OPSNS.description, Literal(i["description"])))
        g.add((u, OPSNS.severity, Literal(i["severity"])))
        g.add((u, OPSNS.openedAt, Literal(i["opened_at"], datatype=XSD.dateTime)))
        if i["deployment"]:
            g.add((u, OPSNS.followsDeployment, D[i["deployment"]]))
        for s in i["symptoms"]:
            g.add((u, OPSNS.hasSymptom, D[s]))
        for a in i["alerts"]:
            g.add((u, OPSNS.raisedAlert, D[a]))
    return g


def build_and_save() -> Graph:
    ds = ensure()
    g = build_graph(ds)
    GRAPH_FILE.write_text(g.serialize(format="turtle"))
    return g


if __name__ == "__main__":
    graph = build_and_save()
    print(f"triples={len(graph)} -> {GRAPH_FILE}")
