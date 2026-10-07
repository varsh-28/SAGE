import json

import pytest

from opsgraph import queries
from opsgraph.config import GOLD_FILE


def _gold(qtype):
    return [q for q in json.loads(GOLD_FILE.read_text()) if q["type"] == qtype]


def test_same_root_cause_matches_python_gold(graph, dataset):
    for q in _gold("M1_same_root_cause"):
        inc = q["question"].split()[-1].rstrip("?")
        assert queries.same_root_cause(graph, inc) == q["gold"], q["question"]


def test_dependent_incidents_match_python_gold(graph, dataset):
    for q in _gold("M3_dependent_incidents"):
        words = q["question"].rstrip("?").split()
        target = words[-1]
        svc = target if not target.startswith("INC-") else queries.service_of(graph, target)[0]
        assert queries.dependent_incidents(graph, svc) == q["gold"], q["question"]


def test_dependents_match_python_gold(graph, dataset):
    for q in _gold("M2_dependents"):
        target = q["question"].rstrip("?").split()[-1]
        svc = target if not target.startswith("INC-") else queries.service_of(graph, target)[0]
        assert queries.dependents(graph, svc) == q["gold"], q["question"]


def test_invalid_ids_are_rejected(graph):
    with pytest.raises(ValueError):
        queries.dependents(graph, "x> } ; DROP ALL #")
