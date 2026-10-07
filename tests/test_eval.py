from opsgraph import evaluate
from opsgraph.classifier import run_classifier


def test_graphrag_beats_vector_on_multihop():
    res = evaluate.run_eval(write=False)
    assert evaluate.check(res) == [], evaluate.check(res)


def test_graphrag_single_hop_is_correct():
    res = evaluate.run_eval(write=False)
    assert res["by_group"]["graphrag"]["single"]["recall"] >= 0.95


def test_classifier_beats_majority_baseline():
    res = run_classifier(write=False)
    assert res["tfidf_logreg"]["f1_macro"] > res["majority_baseline"]["f1_macro"] + 0.2
