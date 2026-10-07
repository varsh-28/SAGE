"""Command line entry point.  python -m opsgraph.cli <command>"""
from __future__ import annotations

import argparse
import json
import sys

from . import classifier, evaluate, generate_data, graph_builder, validate


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="opsgraph")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("generate", help="generate synthetic dataset + gold questions")
    sub.add_parser("build", help="build RDF graph -> data/graph.ttl")
    sub.add_parser("validate", help="SHACL-validate the graph")
    e = sub.add_parser("eval", help="vector-only vs GraphRAG benchmark")
    e.add_argument("--k", type=int, default=5)
    e.add_argument("--with-llm", action="store_true", help="also score LLM answers (needs Ollama)")
    e.add_argument("--check", action="store_true", help="exit 1 if regression thresholds are violated")
    sub.add_parser("classify", help="incident-category classifier")
    a = sub.add_parser("all", help="generate, build, validate, eval, classify")
    a.add_argument("--check", action="store_true")
    args = p.parse_args(argv)

    rc = 0
    if args.cmd in ("generate", "all"):
        ds, gold = generate_data.generate()
        print(f"[generate] incidents={len(ds['incidents'])} services={len(ds['services'])} "
              f"gold_questions={len(gold)}")
    if args.cmd in ("build", "validate", "all"):
        g = graph_builder.build_and_save()
        print(f"[build] triples={len(g)}")
        if args.cmd in ("validate", "all"):
            ok, text = validate.validate_graph(g)
            print("[validate] CONFORMS" if ok else f"[validate] VIOLATIONS\n{text}")
            rc |= 0 if ok else 1
    if args.cmd in ("eval", "all"):
        res = evaluate.run_eval(k=getattr(args, "k", 5), with_llm=getattr(args, "with_llm", False))
        print(f"[eval] backend={res['backend']} questions={res['n_questions']}")
        for sysname, groups in res["by_group"].items():
            for grp, m in groups.items():
                print(f"  {sysname:11s} {grp:6s} recall={m['recall']:.3f} precision={m['precision']:.3f} "
                      f"ctx={m['avg_context_entities']}")
        if getattr(args, "check", False):
            fails = evaluate.check(res)
            for f in fails:
                print(f"[eval] FAIL: {f}")
            rc |= 1 if fails else 0
    if args.cmd in ("classify", "all"):
        res = classifier.run_classifier()
        print("[classify] " + json.dumps({k: v for k, v in res.items() if k.endswith(("baseline", "logreg"))}))
    return rc


if __name__ == "__main__":
    sys.exit(main())
