"""Vector-only RAG vs ontology-grounded GraphRAG over the same incident records.

vector_context : flat retrieval. Each incident record is serialised to text, embedded, top-k returned.
graph_context  : entity linking (INC ids / service names, vector top-1 fallback) -> rule-based intent
                 routing -> templated SPARQL over the RDF graph.

Known limitations (state them in interviews): intent routing is keyword-based, SPARQL is templated
(no LLM text-to-SPARQL), and the graph path gets exact-ID entity linking that the vector baseline does not.
"""
from __future__ import annotations

import json
import re

from . import llm, queries
from .generate_data import ensure
from .graph_builder import build_graph
from .retrieval import VectorIndex

INC_RE = re.compile(r"INC-\d{4}", re.I)


class OpsGraph:
    def __init__(self, ds: dict, backend: str | None = None):
        self.ds = ds
        self.g = build_graph(ds)
        self.inc = {i["id"]: i for i in ds["incidents"]}
        self.rc = {r["id"]: r for r in ds["root_causes"]}
        self.rb = {r["id"]: r["title"] for r in ds["runbooks"]}
        self.env = {e["id"]: e["name"] for e in ds["environments"]}
        self.svc_ids = [s["id"] for s in ds["services"]]
        ids = [i["id"] for i in ds["incidents"]]
        self.index = VectorIndex(backend).fit(ids, [self.doc(i) for i in ids])

    @classmethod
    def load(cls, backend: str | None = None) -> "OpsGraph":
        return cls(ensure(), backend)

    @property
    def backend(self) -> str | None:
        return self.index.backend

    # ------------------------------------------------------------------ records
    def doc(self, inc_id: str) -> str:
        i = self.inc[inc_id]
        rc = self.rc[i["root_cause"]]
        return (f"{i['id']} {i['service']} {self.env[i['env']]} {i['severity']}. {i['description']} "
                f"Root cause: {rc['label']}. Runbook: {self.rb[rc['runbook']]}.")

    def label(self, entity_id: str) -> str:
        if entity_id in self.rc:
            return self.rc[entity_id]["label"]
        if entity_id in self.rb:
            return self.rb[entity_id]
        return entity_id

    # ------------------------------------------------------------------ baseline
    def vector_context(self, question: str, k: int = 5) -> dict:
        hits = self.index.search(question, k)
        entities: list[str] = []
        for inc_id, _ in hits:
            i = self.inc[inc_id]
            rc = self.rc[i["root_cause"]]
            for e in (inc_id, i["service"], i["root_cause"], rc["runbook"]):
                if e not in entities:
                    entities.append(e)
        return {"mode": f"vector_k{k}", "entities": entities, "docs": [h[0] for h in hits],
                "facts": [self.doc(h[0]) for h in hits]}

    # ------------------------------------------------------------------ GraphRAG
    def link(self, question: str) -> tuple[list[str], list[str]]:
        incs = [m.upper() for m in INC_RE.findall(question)]
        incs = [i for i in incs if i in self.inc]
        ql = question.lower()
        svcs = [s for s in self.svc_ids if re.search(rf"(?<![\w-]){re.escape(s)}(?![\w-])", ql)]
        return incs, svcs

    @staticmethod
    def route(question: str) -> str:
        ql = question.lower()
        if "same root cause" in ql:
            return "same_root_cause"
        if "depend" in ql and re.search(r"\bincidents\b", ql):
            return "dependent_incidents"
        if "depend" in ql:
            return "dependents"
        if "runbook" in ql:
            return "runbook"
        if "root cause" in ql:
            return "root_cause"
        return "neighborhood"

    def graph_context(self, question: str) -> dict:
        incs, svcs = self.link(question)
        intent = self.route(question)
        seed = incs[0] if incs else None
        needs_service_only = intent in ("dependents", "dependent_incidents") and svcs
        if seed is None and not needs_service_only:
            seed = self.index.search(question, 1)[0][0]  # vector fallback for entity linking

        entities: list[str] = []
        facts: list[str] = []
        used: list[str] = []
        if intent in ("dependents", "dependent_incidents"):
            svc = svcs[0] if svcs else queries.service_of(self.g, seed)[0]
            if intent == "dependents":
                entities = queries.dependents(self.g, svc)
                facts.append(f"Services depending directly on {svc}: {', '.join(entities) or 'none'}.")
                used.append("dependents")
            else:
                entities = queries.dependent_incidents(self.g, svc)
                facts.append(f"Incidents affecting services that depend on {svc}: {', '.join(entities) or 'none'}.")
                used.append("dependent_incidents")
        elif intent == "same_root_cause":
            entities = queries.same_root_cause(self.g, seed)
            rc = queries.root_cause_of(self.g, seed)[0]
            facts.append(f"Incident {seed} has root cause {self.label(rc)}. "
                         f"Other incidents with the same root cause: {', '.join(entities) or 'none'}.")
            used += ["root_cause_of", "same_root_cause"]
        elif intent == "root_cause":
            entities = queries.root_cause_of(self.g, seed)
            facts.append(f"Incident {seed} has root cause {self.label(entities[0])} ({entities[0]}).")
            used.append("root_cause_of")
        elif intent == "runbook":
            entities = queries.runbook_for(self.g, seed)
            facts.append(f"Incident {seed} is resolved by runbook {self.label(entities[0])} ({entities[0]}).")
            used.append("runbook_for")
        else:
            card = queries.incident_card(self.g, seed)
            entities = [card["service"], card["root_cause"], card["runbook"]]
            facts.append(f"Incident {seed} affects {card['service']} in {card['environment']}; root cause "
                         f"{card['root_cause_label']}; runbook {card['runbook_title']}.")
            used.append("incident_card")
        return {"mode": "graph", "intent": intent, "seed": seed, "entities": entities,
                "facts": facts, "sparql": used}

    # ------------------------------------------------------------------ answers
    def answer(self, question: str, mode: str = "graph", k: int = 5, use_llm: bool = False) -> dict:
        ctx = self.graph_context(question) if mode == "graph" else self.vector_context(question, k)
        text = None
        if use_llm:
            prompt = ("Answer the question using ONLY the context. Cite incident or service ids exactly as "
                      "written. If the context is insufficient, say so.\n\nContext:\n- "
                      + "\n- ".join(ctx["facts"]) + f"\n\nQuestion: {question}\nAnswer:")
            text = llm.generate(prompt)
        if text is None:
            text = " ".join(ctx["facts"]) if mode == "graph" else \
                "Top retrieved incident records: " + ", ".join(ctx["docs"])
        return {"question": question, "mode": mode, "answer": text, "context": ctx,
                "backend": self.backend}


if __name__ == "__main__":
    og = OpsGraph.load()
    print(json.dumps(og.answer("Which other incidents had the same root cause as INC-0042?"), indent=2))
