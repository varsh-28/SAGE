from fastapi.testclient import TestClient

from opsgraph.api import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_ask_graph_same_root_cause():
    r = client.get("/ask", params={"q": "Which other incidents had the same root cause as INC-0001?"})
    body = r.json()
    assert r.status_code == 200
    assert body["context"]["intent"] == "same_root_cause"
    assert body["context"]["seed"] == "INC-0001"


def test_unknown_incident_404():
    assert client.get("/incident/INC-9999").status_code == 404
