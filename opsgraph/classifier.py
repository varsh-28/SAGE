"""Incident-category classifier: TF-IDF + logistic regression vs two baselines."""
from __future__ import annotations

import json

from sklearn.dummy import DummyClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline

from .config import REPORTS_DIR, SEED
from .generate_data import ensure
from .vocab import CATEGORIES

KEYWORDS = {
    "database": ["outdated", "old values", "connection", "timing out", "deadline", "hung"],
    "network": ["tls", "certificate", "handshake", "reset", "unreachable", "health check", "probe"],
    "configuration": ["401", "login", "token", "authentication", "differently", "unexpected fields"],
    "capacity": ["memory", "oomkilled", "heap", "restart", "cpu", "rescheduled", "load average"],
    "deployment": ["release", "regression", "crash loop", "would not start", "readiness"],
    "storage": ["disk", "volume", "space", "writes failed", "429", "rate limited"],
}


def _keyword_predict(texts: list[str], fallback: str) -> list[str]:
    preds = []
    for t in texts:
        tl = t.lower()
        scores = {c: sum(kw in tl for kw in kws) for c, kws in KEYWORDS.items()}
        best = max(scores, key=scores.get)
        preds.append(best if scores[best] > 0 else fallback)
    return preds


def _metrics(y_true, y_pred) -> dict:
    p, r, f, _ = precision_recall_fscore_support(y_true, y_pred, average="macro", zero_division=0)
    return {"accuracy": round(accuracy_score(y_true, y_pred), 3), "precision_macro": round(p, 3),
            "recall_macro": round(r, 3), "f1_macro": round(f, 3)}


def run_classifier(write: bool = True) -> dict:
    ds = ensure()
    X = [i["description"] for i in ds["incidents"]]
    y = [i["category"] for i in ds["incidents"]]
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.3, random_state=SEED, stratify=y)

    majority = DummyClassifier(strategy="most_frequent").fit(Xtr, ytr)
    model = make_pipeline(
        TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=2),
        LogisticRegression(max_iter=2000, C=5.0, class_weight="balanced"),
    ).fit(Xtr, ytr)

    result = {
        "n_train": len(Xtr), "n_test": len(Xte), "classes": CATEGORIES,
        "majority_baseline": _metrics(yte, majority.predict(Xte)),
        "keyword_baseline": _metrics(yte, _keyword_predict(Xte, fallback=majority.predict(Xte[:1])[0])),
        "tfidf_logreg": _metrics(yte, model.predict(Xte)),
    }
    if write:
        REPORTS_DIR.mkdir(exist_ok=True)
        (REPORTS_DIR / "classifier.json").write_text(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    print(json.dumps(run_classifier(), indent=2))
