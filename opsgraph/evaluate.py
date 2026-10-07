"""Benchmark: vector-only RAG vs GraphRAG on the gold question set.

Metrics (retrieval-level, deterministic, no LLM needed):
  recall     = |gold ∩ context entities| / |gold|
  precision  = |gold ∩ context entities| / |context entities|

Optional (--with-llm, needs Ollama):
  answer correctness and hallucination rate.

Gold answers are computed from raw records in pure Python
(generate_data.make_gold), so a correct SPARQL implementation
must independently reproduce them.
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


# ---------------------------------------------------------------------------
# CI REGRESSION THRESHOLDS
# ---------------------------------------------------------------------------
#
# Current measured GraphRAG multi-hop recall:
#     0.833
#
# We use 0.80 as the regression floor so that CI detects a meaningful
# degradation while remaining below the currently measured baseline.
#
# Future improvement target:
#     0.90
#
MIN_GRAPH_MULTI_RECALL = 0.80

# GraphRAG should maintain a meaningful recall improvement over the
# strongest vector-only multi-hop baseline.
MIN_MULTI_RECALL_LIFT = 0.25


def load_gold() -> list[dict]:
    """Load generated and manually authored gold questions."""
    ensure()

    gold = json.loads(GOLD_FILE.read_text())

    if GOLD_MANUAL_FILE.exists():
        # Hand-written questions use the same schema as gold.json.
        gold += json.loads(GOLD_MANUAL_FILE.read_text())

    return gold


def _score(
    ctx_entities: list[str],
    gold: list[str],
) -> tuple[float, float]:
    """Calculate retrieval recall and precision."""
    ents = set(ctx_entities)
    g = set(gold)

    hit = len(ents & g)

    recall = hit / len(g) if g else 0.0
    precision = hit / len(ents) if ents else 0.0

    return recall, precision


def _agg(rows: list[dict]) -> dict:
    """Aggregate retrieval metrics for a group of questions."""
    return {
        "n": len(rows),
        "recall": round(mean(r["recall"] for r in rows), 3),
        "precision": round(mean(r["precision"] for r in rows), 3),
        "avg_context_entities": round(
            mean(r["ctx_size"] for r in rows),
            1,
        ),
    }


def run_eval(
    k: int = 5,
    with_llm: bool = False,
    write: bool = True,
) -> dict:
    """Run the complete vector vs GraphRAG evaluation."""

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

            rec, prec = _score(
                ctx["entities"],
                item["gold"],
            )

            rows.append(
                {
                    "qid": item["id"],
                    "type": item["type"],
                    "group": item["group"],
                    "system": name,
                    "recall": rec,
                    "precision": prec,
                    "ctx_size": len(set(ctx["entities"])),
                }
            )

    by_group = defaultdict(dict)
    by_type = defaultdict(dict)

    for name in systems:
        selected = [
            r for r in rows
            if r["system"] == name
        ]

        for group in ("single", "multi"):
            part = [
                r for r in selected
                if r["group"] == group
            ]

            if part:
                by_group[name][group] = _agg(part)

        for question_type in sorted(
            {r["type"] for r in selected}
        ):
            by_type[name][question_type] = _agg(
                [
                    r
                    for r in selected
                    if r["type"] == question_type
                ]
            )

    result = {
        "backend": og.backend,
        "n_questions": len(gold),
        "k": k,
        "by_group": by_group,
        "by_type": by_type,
        "llm": None,
        "regression_thresholds": {
            "min_graph_multi_recall": MIN_GRAPH_MULTI_RECALL,
            "min_multi_recall_lift": MIN_MULTI_RECALL_LIFT,
        },
    }

    if with_llm:
        if not llm.available():
            result["llm"] = "skipped: Ollama not reachable"
        else:
            result["llm"] = _llm_eval(
                og,
                gold,
                k,
            )

    if write:
        REPORTS_DIR.mkdir(exist_ok=True)

        (
            REPORTS_DIR / "results.json"
        ).write_text(
            json.dumps(
                result,
                indent=2,
            )
        )

        (
            REPORTS_DIR / "results.md"
        ).write_text(
            _markdown(result)
        )

    return result


def _llm_eval(
    og: OpsGraph,
    gold: list[dict],
    k: int,
) -> dict:
    """Evaluate optional LLM-generated answers."""

    out = {}

    for mode, label in (
        ("vector", f"vector_k{k}"),
        ("graph", "graphrag"),
    ):
        correct = []
        halluc = []

        for item in gold:
            res = og.answer(
                item["question"],
                mode=mode,
                k=k,
                use_llm=True,
            )

            text = res["answer"].lower()

            names = [
                og.label(entity).lower()
                for entity in item["gold"]
            ]

            correct.append(
                sum(
                    name in text
                    for name in names
                ) / len(names)
            )

            ctx_text = (
                " ".join(res["context"]["facts"])
                + " "
                + " ".join(res["context"]["entities"])
            )

            cited = set(
                re.findall(
                    r"INC-\d{4}",
                    res["answer"],
                    flags=re.I,
                )
            )

            halluc.append(
                any(
                    citation.upper()
                    not in ctx_text.upper()
                    for citation in cited
                )
            )

        out[label] = {
            "answer_correctness": round(
                mean(correct),
                3,
            ),
            "hallucination_rate": round(
                mean(halluc),
                3,
            ),
            "model": llm.MODEL,
        }

    return out


def _markdown(res: dict) -> str:
    """Generate the Markdown evaluation report."""

    lines = [
        "# OpsGraph evaluation\n",
        (
            f"Vector backend: `{res['backend']}` | "
            f"questions: {res['n_questions']} | "
            f"k={res['k']}"
        ),
        "",
        "Synthetic data; controlled comparison, not a production result.",
        "",
        "## Regression thresholds",
        "",
        (
            f"- Minimum GraphRAG multi-hop recall: "
            f"`{MIN_GRAPH_MULTI_RECALL:.2f}`"
        ),
        (
            f"- Minimum GraphRAG multi-hop recall lift: "
            f"`{MIN_MULTI_RECALL_LIFT:.2f}`"
        ),
        "",
        "## By question group",
        "",
        (
            "| System | Group | n | Recall | Precision | "
            "Avg context entities |"
        ),
        "|---|---|---|---|---|---|",
    ]

    for system_name, groups in res["by_group"].items():
        for group, metrics in groups.items():
            lines.append(
                f"| {system_name} | "
                f"{group}-hop | "
                f"{metrics['n']} | "
                f"{metrics['recall']} | "
                f"{metrics['precision']} | "
                f"{metrics['avg_context_entities']} |"
            )

    lines += [
        "",
        "## By question type",
        "",
        "| System | Type | n | Recall | Precision |",
        "|---|---|---|---|---|",
    ]

    for system_name, types in res["by_type"].items():
        for question_type, metrics in types.items():
            lines.append(
                f"| {system_name} | "
                f"{question_type} | "
                f"{metrics['n']} | "
                f"{metrics['recall']} | "
                f"{metrics['precision']} |"
            )

    if isinstance(res.get("llm"), dict):
        lines += [
            "",
            "## LLM answers",
            "",
            "| System | Correctness | Hallucination rate |",
            "|---|---|---|",
        ]

        for system_name, metrics in res["llm"].items():
            lines.append(
                f"| {system_name} | "
                f"{metrics['answer_correctness']} | "
                f"{metrics['hallucination_rate']} |"
            )

    return "\n".join(lines) + "\n"


def check(result: dict) -> list[str]:
    """Regression gate used by CI.

    Returns:
        Empty list when the evaluation passes.
        List of failure messages when one or more gates fail.
    """

    fails = []

    # ---------------------------------------------------------------
    # GraphRAG multi-hop recall gate
    # ---------------------------------------------------------------

    graph = result["by_group"]["graphrag"]["multi"]["recall"]

    if graph < MIN_GRAPH_MULTI_RECALL:
        fails.append(
            "graphrag multi-hop recall "
            f"{graph:.3f} < "
            f"{MIN_GRAPH_MULTI_RECALL:.2f}"
        )

    # ---------------------------------------------------------------
    # Vector baseline
    # ---------------------------------------------------------------

    vector_systems = [
        name
        for name in result["by_group"]
        if name.startswith("vector_k")
    ]

    best_vec = max(
        result["by_group"][name]["multi"]["recall"]
        for name in vector_systems
    )

    # ---------------------------------------------------------------
    # GraphRAG lift gate
    # ---------------------------------------------------------------

    recall_lift = graph - best_vec

    if recall_lift < MIN_MULTI_RECALL_LIFT:
        fails.append(
            "graph lift over best vector "
            f"{recall_lift:.3f} < "
            f"{MIN_MULTI_RECALL_LIFT:.2f}"
        )

    return fails