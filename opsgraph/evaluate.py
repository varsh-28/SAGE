"""Benchmark: vector-only RAG vs GraphRAG on the gold question set.

Metrics (retrieval-level, deterministic, no LLM needed):
  recall     = |gold ∩ context entities| / |gold|
  precision  = |gold ∩ context entities| / |context entities|
Optional (--with-llm, needs Ollama): answer correctness and hallucination rate.

Gold answers are computed from raw records in pure Python (generate_data.make_gold), so a correct
SPARQL implementation must independently reproduce them.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from statistics import mean

from . import llm
from .config import GOLD_FILE, GOLD_MANUAL_FILE, REPORTS_DIR
from .generate_data import ensure
from .graphrag import OpsGraph

MIN_GRAPH_MULTI_RECALL = 0.90
MIN_MULTI_RECALL_LIFT = 0.25  # graph recall minus best vector recall on multi-hop questions


def load_gold() -> list[dict]:
    ensure()
    gold = json.loads(GOLD_FILE.read_text())
    if GOLD_MANUAL_FILE.exists():  # hand-written questions: same schema as gold.json
        gold += json.loads(GOLD_MANUAL_FILE.read_text())
    return gold


def _score(ctx_entities: list[str], gold: list[str]) -> tuple[float, float]:
    ents, g = set(ctx_entities), set(gold)
    hit = len(ents & g)
    return (hit / len(g) if g else 0.0), (hit / len(ents) if ents else 0.0)


def _agg(rows: list[dict]) -> dict:
    return {"n": len(rows),
            "recall": round(mean(r["recall"] for r in rows), 3),
            "precision": round(mean(r["precision"] for r in rows), 3),
            "avg_context_entities": round(mean(r["ctx_size"] for r in rows), 1)}


def run_eval(k: int = 5, with_llm: bool = False, write: bool = True) -> dict:
    og = OpsGraph.load()
    gold = load_gold()
    systems = {
        f"vector_k{k}": lambda q: og.vector_context(q, k),
        "vector_k20": lambda q: og.vector_context(q, 20),
        "graphrag": og.graph_context,
    }
    rows = []
    for item in gold:
        for name, fn in systems.items():
            ctx = fn(item["question"])
            rec, prec = _score(ctx["entities"], item["gold"])
            rows.append({"qid": item["id"], "type": item["type"], "group": item["group"], "system": name,
                         "recall": rec, "precision": prec, "ctx_size": len(set(ctx["entities"]))})

    by_group, by_type = defaultdict(dict), defaultdict(dict)
    for name in systems:
        sel = [r for r in rows if r["system"] == name]
        for grp in ("single", "multi"):
            part = [r for r in sel if r["group"] == grp]
            if part:
                by_group[name][grp] = _agg(part)
        for t in sorted({r["type"] for r in sel}):
            by_type[name][t] = _agg([r for r in sel if r["type"] == t])

    result = {"backend": og.backend, "n_questions": len(gold), "k": k,
              "by_group": by_group, "by_type": by_type, "llm": None}

    if with_llm:
        if not llm.available():
            result["llm"] = "skipped: Ollama not reachable"
        else:
            result["llm"] = _llm_eval(og, gold, k)

    if write:
        REPORTS_DIR.mkdir(exist_ok=True)
        (REPORTS_DIR / "results.json").write_text(json.dumps(result, indent=2))
        (REPORTS_DIR / "results.md").write_text(_markdown(result))
    return result


def _llm_eval(og: OpsGraph, gold: list[dict], k: int) -> dict:
    out = {}
    for mode, label in (("vector", f"vector_k{k}"), ("graph", "graphrag")):
        correct, halluc = [], []
        for item in gold:
            res = og.answer(item["question"], mode=mode, k=k, use_llm=True)
            text = res["answer"].lower()
            names = [og.label(e).lower() for e in item["gold"]]
            correct.append(sum(n in text for n in names) / len(names))
            ctx_text = " ".join(res["context"]["facts"]) + " " + " ".join(res["context"]["entities"])
            cited = set(re.findall(r"INC-\d{4}", res["answer"], flags=re.I))
            halluc.append(any(c.upper() not in ctx_text.upper() for c in cited))
        out[label] = {"answer_correctness": round(mean(correct), 3),
                      "hallucination_rate": round(mean(halluc), 3), "model": llm.MODEL}
    return out


def _markdown(res: dict) -> str:
    lines = [f"# OpsGraph evaluation\n",
             f"Vector backend: `{res['backend']}` | questions: {res['n_questions']} | k={res['k']}",
             "", "Synthetic data; controlled comparison, not a production result.", "",
             "## By question group", "", "| System | Group | n | Recall | Precision | Avg context entities |",
             "|---|---|---|---|---|---|"]
    for sysname, groups in res["by_group"].items():
        for grp, m in groups.items():
            lines.append(f"| {sysname} | {grp}-hop | {m['n']} | {m['recall']} | {m['precision']} | "
                         f"{m['avg_context_entities']} |")
    lines += ["", "## By question type", "", "| System | Type | n | Recall | Precision |", "|---|---|---|---|---|"]
    for sysname, types in res["by_type"].items():
        for t, m in types.items():
            lines.append(f"| {sysname} | {t} | {m['n']} | {m['recall']} | {m['precision']} |")
    if isinstance(res.get("llm"), dict):
        lines += ["", "## LLM answers", "", "| System | Correctness | Hallucination rate |", "|---|---|---|"]
        for sysname, m in res["llm"].items():
            lines.append(f"| {sysname} | {m['answer_correctness']} | {m['hallucination_rate']} |")
    return "\n".join(lines) + "\n"


def check(result: dict) -> list[str]:
    """Regression gate used by CI. Returns a list of failures (empty = pass)."""
    fails = []
    graph = result["by_group"]["graphrag"]["multi"]["recall"]
    vec_name = next(n for n in result["by_group"] if n.startswith("vector_k") and n != "vector_k20")
    best_vec = max(result["by_group"][n]["multi"]["recall"] for n in result["by_group"] if n != "graphrag")
    if graph < MIN_GRAPH_MULTI_RECALL:
        fails.append(f"graphrag multi-hop recall {graph} < {MIN_GRAPH_MULTI_RECALL}")
    if graph - best_vec < MIN_MULTI_RECALL_LIFT:
        fails.append(f"graph lift over best vector ({vec_name} family) {graph - best_vec:.3f} "
                     f"< {MIN_MULTI_RECALL_LIFT}")
    return fails
