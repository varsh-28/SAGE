"""Synthetic data generator.

Produces data/dataset.json (the raw records) and data/gold.json (benchmark questions with
gold answers computed directly from the raw records, independent of SPARQL).

The data is SYNTHETIC. Results measured on it are a controlled comparison, not a production result.
"""
from __future__ import annotations

import datetime as dt
import json
import random
from collections import defaultdict

from .config import DATA_DIR, DATASET_FILE, GOLD_FILE, N_INCIDENTS, SEED
from .vocab import (CATEGORIES, ENVIRONMENTS, N_PLATFORM, ROOT_CAUSES, RUNBOOKS,
                    SERVICE_LIST, SYMPTOMS)

TEMPLATES = [
    "{svc} in {env}: {s1}. Shortly after, {s2}.",
    "On-call was paged for {svc} ({env}). {S1}; later {s2}.",
    "Customers reported trouble with {svc}. {S1}, and {s2}.",
    "{env} - {svc} degraded. {S1}. Also noted: {s2}.",
]


def _cap(text: str) -> str:
    return text[:1].upper() + text[1:]


def build_dataset(seed: int = SEED, n_incidents: int = N_INCIDENTS) -> dict:
    rng = random.Random(seed)

    # ---- services and dependency DAG (edges only point to earlier services => no cycles)
    services = []
    for i, (name, tier) in enumerate(SERVICE_LIST):
        if i < N_PLATFORM:
            deps = []
        else:
            k = min(rng.choice([1, 2, 2, 3]), i)
            deps = [SERVICE_LIST[j][0] for j in sorted(rng.sample(range(i), k))]
        services.append({"id": name, "name": name, "tier": tier, "depends_on": deps})

    environments = [{"id": "env_" + e.replace("-", "_"), "name": e} for e in ENVIRONMENTS]
    env_by_id = {e["id"]: e for e in environments}

    root_causes = [
        {"id": rid, "label": label, "category": cat, "symptoms": syms, "runbook": rb}
        for rid, (label, cat, syms, rb) in ROOT_CAUSES.items()
    ]
    runbooks = [{"id": rid, "title": title} for rid, title in RUNBOOKS.items()]
    symptoms = [
        {"id": "sym_" + key, "key": key, "label": m["label"], "group": m["group"], "alt": m["alt"]}
        for key, m in SYMPTOMS.items()
    ]

    deployments, alerts, incidents = [], [], []

    def new_deployment(svc_id: str, env_id: str, when: dt.datetime) -> str:
        did = f"dep_{len(deployments) + 1:04d}"
        deployments.append({
            "id": did, "service": svc_id, "env": env_id,
            "version": f"v{rng.randint(1, 4)}.{rng.randint(0, 9)}.{rng.randint(0, 9)}",
            "deployed_at": when.isoformat(),
        })
        return did

    # ---- incidents. Root cause weights are skewed so some causes recur often.
    rc_ids = list(ROOT_CAUSES)
    weights = [rng.choice([1, 2, 3, 5]) for _ in rc_ids]
    start, span_days = dt.datetime(2025, 1, 1), 640

    for n in range(1, n_incidents + 1):
        rc_id = rng.choices(rc_ids, weights)[0]
        label, category, rc_syms, runbook = ROOT_CAUSES[rc_id]
        svc = rng.choice(services)
        env = rng.choice(environments)
        opened = start + dt.timedelta(days=rng.randrange(span_days), minutes=rng.randrange(1440))

        syms = rng.sample(rc_syms, k=min(len(rc_syms), rng.choice([2, 2, 3])))
        distractor = None
        if rng.random() < 0.4:
            others = [s for s in SYMPTOMS if s not in rc_syms]
            distractor = rng.choice(others)

        dep_id = None
        dep_version = None
        if rng.random() < (0.85 if category == "deployment" else 0.3):
            dep_id = new_deployment(svc["id"], env["id"], opened - dt.timedelta(hours=rng.randint(1, 48)))
            dep_version = deployments[-1]["version"]

        phrases = [rng.choice(SYMPTOMS[s]["phrases"]) for s in syms]
        text = rng.choice(TEMPLATES).format(
            svc=svc["name"], env=env_by_id[env["id"]]["name"],
            s1=phrases[0], S1=_cap(phrases[0]), s2=phrases[1])
        if len(phrases) > 2:
            text += f" Additionally, {phrases[2]}."
        if dep_version:
            text += f" Started shortly after release {dep_version}."
        if distractor:
            text += f" Possibly unrelated: {rng.choice(SYMPTOMS[distractor]['phrases'])}."
        if rng.random() < 0.15:
            text += f" Initial triage suggests: {label.lower()}."

        inc_id = f"INC-{n:04d}"
        alert_ids = []
        for s in syms[: rng.choice([1, 2])]:
            aid = f"alert_{len(alerts) + 1:04d}"
            alerts.append({"id": aid, "name": SYMPTOMS[s]["alert"], "incident": inc_id})
            alert_ids.append(aid)

        incidents.append({
            "id": inc_id, "service": svc["id"], "env": env["id"], "deployment": dep_id,
            "root_cause": rc_id, "symptoms": ["sym_" + s for s in syms + ([distractor] if distractor else [])],
            "alerts": alert_ids, "severity": rng.choices(["SEV1", "SEV2", "SEV3", "SEV4"], [1, 3, 4, 2])[0],
            "opened_at": opened.isoformat(), "description": text, "category": category,
        })

    # background deployments with no incident
    for _ in range(60):
        svc, env = rng.choice(services), rng.choice(environments)
        new_deployment(svc["id"], env["id"], start + dt.timedelta(days=rng.randrange(span_days)))

    return {
        "meta": {"seed": seed, "n_incidents": n_incidents, "synthetic": True},
        "services": services, "environments": environments, "root_causes": root_causes,
        "runbooks": runbooks, "symptoms": symptoms, "deployments": deployments,
        "alerts": alerts, "incidents": incidents,
    }


def make_gold(ds: dict, seed: int = SEED) -> list[dict]:
    """Gold answers computed from raw records (pure Python), not from the graph."""
    rng = random.Random(seed + 1)
    inc = {i["id"]: i for i in ds["incidents"]}
    rc_label = {r["id"]: r for r in ds["root_causes"]}
    dependents = defaultdict(list)
    for s in ds["services"]:
        for d in s["depends_on"]:
            dependents[d].append(s["id"])
    inc_by_rc, inc_by_svc = defaultdict(list), defaultdict(list)
    for i in ds["incidents"]:
        inc_by_rc[i["root_cause"]].append(i["id"])
        inc_by_svc[i["service"]].append(i["id"])

    def incs_on_dependents(svc):
        return sorted({x for d in dependents[svc] for x in inc_by_svc[d]})

    def pick(pool, n):
        return rng.sample(pool, min(n, len(pool)))

    all_inc = sorted(inc)
    gold: list[dict] = []

    def add(qtype, group, question, answer):
        gold.append({"id": f"q{len(gold) + 1:03d}", "type": qtype, "group": group,
                     "question": question, "gold": sorted(answer)})

    for i in pick(all_inc, 15):
        add("S1_root_cause", "single", f"What was the root cause of incident {i}?", [inc[i]["root_cause"]])
    for i in pick(all_inc, 10):
        rb = rc_label[inc[i]["root_cause"]]["runbook"]
        add("S2_runbook", "single", f"Which runbook should be followed for incident {i}?", [rb])
    for i in pick([x for x in all_inc if len(inc_by_rc[inc[x]["root_cause"]]) >= 3], 20):
        others = [x for x in inc_by_rc[inc[i]["root_cause"]] if x != i]
        add("M1_same_root_cause", "multi", f"Which other incidents had the same root cause as {i}?", others)
    for i in pick([x for x in all_inc if dependents[inc[x]["service"]]], 8):
        add("M2_dependents", "multi",
            f"Which services depend directly on the service that failed in {i}?", dependents[inc[i]["service"]])
    for s in pick([s["id"] for s in ds["services"] if dependents[s["id"]]], 7):
        add("M2_dependents", "multi", f"Which services depend directly on {s}?", dependents[s])
    for i in pick([x for x in all_inc if incs_on_dependents(inc[x]["service"])], 8):
        add("M3_dependent_incidents", "multi",
            f"Which incidents affected services that depend on the service that failed in {i}?",
            incs_on_dependents(inc[i]["service"]))
    for s in pick([s["id"] for s in ds["services"] if incs_on_dependents(s["id"])], 7):
        add("M3_dependent_incidents", "multi",
            f"Which incidents hit services that depend on {s}?", incs_on_dependents(s))
    return gold


def generate(seed: int = SEED, n_incidents: int = N_INCIDENTS) -> tuple[dict, list[dict]]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ds = build_dataset(seed, n_incidents)
    gold = make_gold(ds, seed)
    DATASET_FILE.write_text(json.dumps(ds, indent=1))
    GOLD_FILE.write_text(json.dumps(gold, indent=1))
    return ds, gold


def ensure() -> dict:
    """Return the dataset, generating it first if it does not exist."""
    if not DATASET_FILE.exists() or not GOLD_FILE.exists():
        generate()
    return json.loads(DATASET_FILE.read_text())


if __name__ == "__main__":
    ds, gold = generate()
    print(f"incidents={len(ds['incidents'])} services={len(ds['services'])} gold_questions={len(gold)}")
