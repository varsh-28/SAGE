"""FastAPI service. Run: uvicorn opsgraph.api:app --reload  (docs at /docs)."""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query

from . import queries
from .graphrag import OpsGraph

app = FastAPI(title="OpsGraph", version="0.1.0",
              description="Ontology-grounded GraphRAG over synthetic cloud-ops incidents.")
_og: OpsGraph | None = None


def get_og() -> OpsGraph:
    global _og
    if _og is None:
        _og = OpsGraph.load()
    return _og


@app.get("/health")
def health():
    og = get_og()
    return {"status": "ok", "triples": len(og.g), "incidents": len(og.inc), "vector_backend": og.backend}


@app.get("/ask")
def ask(q: str = Query(..., min_length=3), mode: str = Query("graph", pattern="^(graph|vector)$"),
        k: int = Query(5, ge=1, le=50), llm: bool = False):
    return get_og().answer(q, mode=mode, k=k, use_llm=llm)


@app.get("/incident/{incident_id}")
def incident(incident_id: str):
    og = get_og()
    incident_id = incident_id.upper()
    if incident_id not in og.inc:
        raise HTTPException(404, f"unknown incident {incident_id}")
    card = queries.incident_card(og.g, incident_id)
    card["same_root_cause"] = queries.same_root_cause(og.g, incident_id)
    card["description"] = og.inc[incident_id]["description"]
    return card


@app.get("/service/{service_id}")
def service(service_id: str):
    og = get_og()
    if service_id not in og.svc_ids:
        raise HTTPException(404, f"unknown service {service_id}")
    return {"service": service_id,
            "depends_on": queries.dependencies(og.g, service_id),
            "dependents": queries.dependents(og.g, service_id),
            "incidents_on_dependents": queries.dependent_incidents(og.g, service_id)}
