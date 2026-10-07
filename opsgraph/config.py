from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
ONTOLOGY_DIR = ROOT / "ontology"
REPORTS_DIR = ROOT / "reports"

ONTOLOGY_FILE = ONTOLOGY_DIR / "opsgraph.ttl"
SHAPES_FILE = ONTOLOGY_DIR / "shapes.ttl"
DATASET_FILE = DATA_DIR / "dataset.json"
GOLD_FILE = DATA_DIR / "gold.json"
GOLD_MANUAL_FILE = DATA_DIR / "gold_manual.json"  # optional: your hand-written questions
GRAPH_FILE = DATA_DIR / "graph.ttl"

# Namespaces
OPS = "https://example.org/opsgraph/ontology#"
DATA = "https://example.org/opsgraph/data/"

SEED = 42
N_INCIDENTS = 300
