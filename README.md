# OpsGraph — Ontology-Grounded GraphRAG for Enterprise Incident Diagnosis

OpsGraph is an experimental **GraphRAG-based enterprise incident diagnosis system** that combines knowledge graphs, ontology-driven semantics, SPARQL retrieval, vector search, and optional local LLM generation.

The project investigates a practical question:

> **Can explicit operational relationships improve retrieval for multi-hop incident-diagnosis questions compared with vector-only retrieval?**

OpsGraph models relationships between:

- Incidents
- Services
- Environments
- Deployments
- Alerts
- Dependencies
- Root causes
- Runbooks
- Symptoms

The system compares **TF-IDF vector retrieval** against **GraphRAG retrieval** on a controlled synthetic incident-diagnosis benchmark.

> **Important:** All current benchmark data is synthetic. The reported results demonstrate the retrieval mechanism in a controlled experiment and should not be interpreted as production accuracy.

---

## 🎯 Problem Statement

Enterprise incident investigation often requires engineers to correlate information across multiple operational systems.

For example:

```text
Incident
   ↓
Affected Service
   ↓
Dependency
   ↓
Related Service
   ↓
Alert
   ↓
Root Cause
   ↓
Runbook
```

A traditional vector search system primarily retrieves information based on semantic similarity.

However, many operational questions are **relational or multi-hop**:

> "Which incidents are associated with services depending on the service affected by this incident?"

Answering this requires following explicit relationships rather than simply finding text that looks similar.

OpsGraph addresses this problem by representing operational knowledge as a structured graph and using graph traversal to build a more targeted retrieval context.

---

# 🏗️ Architecture

```text
                    ┌─────────────────────┐
                    │ Synthetic Incident  │
                    │       Data          │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Ontology + Concepts │
                    │ OWL / RDFS / SKOS   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    RDF Graph        │
                    │      Builder        │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    SHACL Validation │
                    └──────────┬──────────┘
                               │
                  ┌────────────┴────────────┐
                  │                         │
                  ▼                         ▼
        ┌──────────────────┐      ┌──────────────────┐
        │ Vector Retrieval │      │ Graph Retrieval  │
        │ TF-IDF / ST      │      │ SPARQL / Graph   │
        └────────┬─────────┘      └────────┬─────────┘
                 │                         │
                 ▼                         ▼
        ┌──────────────────┐      ┌──────────────────┐
        │ Vector-only RAG  │      │     GraphRAG     │
        └────────┬─────────┘      └────────┬─────────┘
                 │                         │
                 └────────────┬────────────┘
                              ▼
                    ┌─────────────────────┐
                    │ Retrieval Evaluation│
                    │ Recall / Precision  │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Optional Local LLM  │
                    │      Ollama          │
                    └─────────────────────┘
```

---

# 🔑 Key Idea

Vector retrieval answers:

> **"Which records look similar to my question?"**

Graph retrieval answers:

> **"Which entities are structurally connected to the entities involved in my question?"**

For example:

```text
Incident
   │
   └── affects ──► Payment Service
                         │
                         ├── depends_on ──► Database
                         │
                         ├── has_alert ──► Connection Pool Alert
                         │
                         └── caused_by ──► Connection Saturation
                                                  │
                                                  └── addressed_by
                                                           │
                                                           ▼
                                                        Runbook
```

This structure is particularly useful for multi-hop operational questions.

---

# 🧠 Technologies

| Area | Technology |
|---|---|
| Language | Python |
| Knowledge Graph | RDFLib |
| Ontology | OWL / RDFS |
| Vocabulary | SKOS |
| Validation | SHACL / pySHACL |
| Query Language | SPARQL |
| Vector Retrieval | TF-IDF |
| Optional Embeddings | Sentence Transformers |
| Optional LLM | Ollama |
| LLM Model | llama3.2:3b |
| API | FastAPI |
| Testing | Pytest |
| Containerization | Docker |
| CI | GitHub Actions |
| ML Classification | Scikit-learn |

---

# 📂 Project Structure

```text
OpsGraph/
│
├── ontology/
│   ├── opsgraph.ttl
│   └── shapes.ttl
│
├── opsgraph/
│   ├── vocab.py
│   ├── generate_data.py
│   ├── graph_builder.py
│   ├── validate.py
│   ├── queries.py
│   ├── retrieval.py
│   ├── graphrag.py
│   ├── llm.py
│   ├── evaluate.py
│   ├── classifier.py
│   ├── api.py
│   └── cli.py
│
├── data/
│   └── gold_manual.json
│
├── tests/
│
├── docs/
│   ├── architecture.md
│   └── rdf_vs_property_graph.md
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── requirements-optional.txt
└── README.md
```

---

# 🚀 Quick Start

## 1. Clone the repository

```bash
git clone https://github.com/varsh-28/opsgraph.git
cd opsgraph
```

## 2. Create a virtual environment

### Windows

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### Linux / macOS

```bash
python -m venv .venv
source .venv/bin/activate
```

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

## 4. Run the complete pipeline

```bash
python -m opsgraph.cli all
```

The pipeline performs:

```text
Generate synthetic data
        ↓
Build RDF graph
        ↓
Validate graph using SHACL
        ↓
Run vector vs GraphRAG evaluation
        ↓
Run incident classification
```

---

# 🧪 Run Tests

```bash
pytest -q
```

The current project test suite passes successfully.

---

# 📊 Evaluation

The current benchmark contains:

- **90 questions**
- **30 single-hop questions**
- **60 multi-hop questions**
- TF-IDF vector retrieval
- GraphRAG retrieval
- Top-5 and Top-20 vector retrieval comparisons

The evaluation measures:

- Recall
- Precision
- Average retrieved context entities

---

# 📈 Benchmark Results

The following results were produced locally using the TF-IDF backend.

> **Dataset:** Synthetic  
> **Purpose:** Controlled retrieval comparison  
> **Not:** Production accuracy measurement

## Results by Question Group

| System | Group | Questions | Recall | Precision | Avg. Context Entities |
|---|---:|---:|---:|---:|---:|
| vector_k5 | Single-hop | 30 | 0.833 | 0.049 | 17.0 |
| vector_k5 | Multi-hop | 60 | 0.037 | 0.005 | 15.7 |
| vector_k20 | Single-hop | 30 | 0.833 | 0.015 | 53.5 |
| vector_k20 | Multi-hop | 60 | 0.170 | 0.014 | 49.6 |
| GraphRAG | Single-hop | 30 | 0.833 | 0.833 | 1.2 |
| GraphRAG | Multi-hop | 60 | 0.833 | 0.833 | 11.9 |

---

# 🔍 What the Results Show

The strongest difference appears on **multi-hop questions**.

### Vector-only RAG — Top 5

```text
Recall:    3.7%
Precision: 0.5%
```

### Vector-only RAG — Top 20

```text
Recall:    17.0%
Precision: 1.4%
```

Increasing `k` gives vector retrieval more opportunities to find relevant information, but it also increases the amount of retrieved context substantially.

Average context increased from:

```text
~15.7 entities
```

to:

```text
~49.6 entities
```

for multi-hop questions.

### GraphRAG

```text
Recall:    83.3%
Precision: 83.3%
```

with approximately:

```text
11.9 context entities
```

on average for multi-hop questions.

This controlled experiment suggests that explicit graph relationships can provide more targeted retrieval for relational incident-diagnosis questions.

---

# 🧩 Evaluation by Question Type

The benchmark includes several structured question categories.

## Multi-hop

| Question Type | GraphRAG Recall | GraphRAG Precision |
|---|---:|---:|
| M1_same_root_cause | 1.000 | 1.000 |
| M2_dependents | 1.000 | 1.000 |
| M3_dependent_incidents | 1.000 | 1.000 |

## Single-hop

| Question Type | GraphRAG Recall | GraphRAG Precision |
|---|---:|---:|
| S1_root_cause | 1.000 | 1.000 |
| S2_runbook | 1.000 | 1.000 |

Additional manually authored question categories are currently present in the benchmark but are not yet integrated into the same intent/entity-linking evaluation path. These currently produce zero scores and are therefore **not included in the headline GraphRAG result**.

---

# 🤖 Incident Classification

OpsGraph also includes an incident-category classification experiment.

The current comparison evaluates:

```text
Majority baseline
       ↓
Keyword rules
       ↓
TF-IDF + Logistic Regression
```

Current results:

| Classifier | Accuracy | Macro-F1 |
|---|---:|---:|
| Majority baseline | 0.267 | 0.070 |
| Keyword rules | 0.478 | 0.441 |
| TF-IDF + Logistic Regression | 0.689 | 0.669 |

The classifier provides an additional ML component for categorizing operational incidents.

---

# 🧠 GraphRAG Workflow

A simplified GraphRAG workflow is:

```text
User Question
      │
      ▼
Intent Detection
      │
      ▼
Entity Identification
      │
      ▼
Graph Relationship Traversal
      │
      ▼
SPARQL Retrieval
      │
      ▼
Relevant Graph Context
      │
      ▼
Optional LLM
      │
      ▼
Natural Language Answer
```

The current graph path uses:

- Exact-ID entity linking
- Keyword-based intent routing
- Templated SPARQL queries

This is intentional for the controlled benchmark.

---

# 🛡️ Ontology and SHACL Validation

OpsGraph uses an ontology to define the semantic structure of operational entities.

Example conceptual relationships:

```text
Incident ──affects──────► Service

Service ──depends_on────► Service

Service ──has_alert─────► Alert

Incident ──caused_by────► RootCause

RootCause ──has_runbook► Runbook
```

SHACL is used to validate graph constraints such as:

- Required properties
- Expected classes
- Cardinality
- Enumerated values
- Dependency constraints
- Graph consistency rules

This helps prevent malformed operational knowledge from entering the retrieval layer.

---

# 🌐 API

OpsGraph includes a FastAPI application.

Start the API with:

```bash
uvicorn opsgraph.api:app --reload
```

API documentation:

```text
http://127.0.0.1:8000/docs
```

The API exposes the project functionality through HTTP endpoints for integration and testing.

---

# 🐳 Docker

The project includes Docker support.

Build and run:

```bash
docker compose up --build
```

The API is exposed on:

```text
http://127.0.0.1:8000
```

The default Docker configuration uses the TF-IDF backend.

---

# 🤖 Optional Local LLM

OpsGraph can optionally use a locally running Ollama model.

Install Ollama and pull the model:

```bash
ollama pull llama3.2:3b
```

Verify:

```bash
ollama list
```

Then:

```bash
python -m opsgraph.cli eval --with-llm
```

The LLM layer is optional and is currently treated as an experimental generation layer rather than part of the headline retrieval benchmark.

The retrieval benchmark can be executed independently of the LLM.

---

# 🧪 Testing Strategy

The project includes automated tests covering areas such as:

```text
Ontology / SHACL validation
        ↓
SPARQL queries
        ↓
Retrieval / evaluation
        ↓
API behavior
```

Run:

```bash
pytest -q
```

The current test suite passes successfully.

---

# 🔬 Design Decisions

## Why RDF?

RDF provides a standards-based representation for relationships between operational entities.

It also works naturally with:

- OWL
- RDFS
- SKOS
- SHACL
- SPARQL

## Why GraphRAG?

Traditional RAG is useful for semantic similarity search.

GraphRAG becomes useful when the question requires explicit relationships:

```text
Incident
   ↓
Service
   ↓
Dependency
   ↓
Related Service
   ↓
Incident
```

The graph preserves these relationships instead of treating every retrieved document as an independent piece of text.

## Why keep vector retrieval?

Vector retrieval remains valuable for:

- Unstructured incident descriptions
- Logs
- Runbooks
- Natural-language symptoms
- Fuzzy semantic matching

Therefore, a production architecture would likely use **hybrid retrieval** rather than replacing vector retrieval completely.

---

# ⚠️ Current Limitations

This project is intentionally a controlled research/engineering experiment.

### 1. Synthetic data

All current benchmark data is synthetic.

The results should not be interpreted as production performance.

### 2. Exact-ID entity linking

The current graph path uses exact entity identifiers.

Real enterprise data would require more robust entity resolution.

### 3. Keyword intent routing

Intent selection currently uses deterministic keyword-based logic.

A production implementation could use a trained classifier or LLM-based intent detection.

### 4. Templated SPARQL

SPARQL queries are currently predefined templates.

Natural-language-to-SPARQL generation is a future improvement.

### 5. LLM evaluation

The current headline benchmark measures **retrieval quality**, not end-to-end LLM answer correctness.

A stronger future benchmark should evaluate:

- Answer correctness
- Faithfulness
- Hallucination rate
- Evidence attribution
- Latency
- Token usage

---

# 🚀 Future Improvements

## 1. Hybrid Retrieval

Combine:

```text
Vector similarity
        +
Graph traversal
        +
Metadata filtering
```

to handle both semantic and relational queries.

## 2. Better Entity Linking

Replace exact-ID matching with:

```text
Question
   ↓
Entity extraction
   ↓
Entity resolution
   ↓
Canonical graph entity
```

This would make the system more realistic for enterprise data.

## 3. Natural Language → SPARQL

Introduce controlled query generation:

```text
Natural Language
       ↓
Intent
       ↓
Entities
       ↓
SPARQL
       ↓
Knowledge Graph
```

with validation before execution.

## 4. Evidence and Provenance

Every generated recommendation should expose its supporting graph path:

```text
Incident
   ↓
Service
   ↓
Dependency
   ↓
Root Cause
   ↓
Runbook
```

This makes the system more explainable and easier for engineers to trust.

## 5. Temporal Reasoning

Enterprise incidents are time-dependent.

Future versions could model:

```text
Deployment
     ↓
Deployment Time
     ↓
Alert
     ↓
Incident
```

and answer questions such as:

> "Did the incident occur shortly after a deployment?"

## 6. AI-Powered Failure Analysis

A future extension could connect OpsGraph with automated testing and CI/CD systems.

Example:

```text
Failed Test
     ↓
Exception / Stack Trace
     ↓
Failure Classification
     ↓
Related Service
     ↓
Known Incident / Root Cause
     ↓
Recommended Investigation
     ↓
Runbook
```

This could evolve the project toward an **AIOps and intelligent failure-analysis platform**.

---

# 🎯 Enterprise Use Case

A potential enterprise deployment could integrate:

```text
Monitoring
     │
     ├── Alerts
     ├── Metrics
     └── Logs
          │
          ▼
Incident Management
          │
          ▼
      OpsGraph
          │
    ┌─────┴─────┐
    ▼           ▼
Knowledge    Service
Graph        Dependencies
    │           │
    └─────┬─────┘
          ▼
      GraphRAG
          │
          ▼
      LLM / AI
          │
          ▼
Engineer Investigation
```

Potential benefits include:

- Faster incident investigation
- Better correlation of operational information
- Relationship-aware retrieval
- Reduced irrelevant context
- Explainable investigation paths
- Reusable operational knowledge
- Foundation for future AIOps automation

The goal is **decision support for engineers**, not autonomous production remediation.

---

# 📌 Interview Summary

### Problem

Enterprise incident diagnosis requires correlating information across many operational entities and systems.

### Solution

Build an ontology-grounded knowledge graph and use GraphRAG to retrieve relationship-aware context.

### Key comparison

```text
Vector-only RAG
→ semantic similarity

GraphRAG
→ semantic question
→ entity identification
→ graph relationships
→ targeted context
```

### Key result

For the current controlled synthetic benchmark:

```text
Multi-hop Vector Top-5
Recall:    3.7%
Precision: 0.5%

Multi-hop GraphRAG
Recall:    83.3%
Precision: 83.3%
```

### Main conclusion

> **The experiment suggests that explicit graph relationships can substantially improve retrieval for multi-hop enterprise incident-diagnosis questions compared with TF-IDF similarity retrieval.**

---

# 📚 Learning Areas Demonstrated

This project demonstrates hands-on work with:

- Python
- Knowledge Graphs
- RDF
- OWL / RDFS
- SKOS
- SHACL
- SPARQL
- GraphRAG
- RAG
- TF-IDF
- Scikit-learn
- FastAPI
- Pytest
- Docker
- GitHub Actions
- Ollama
- Enterprise incident diagnosis concepts

---

# ⚖️ Project Disclaimer

This is an experimental portfolio and learning project.

The current benchmark uses synthetic data and controlled question sets. GraphRAG currently benefits from exact-ID entity linking and templated SPARQL queries.

The reported metrics demonstrate the behavior of the implemented retrieval mechanisms under the benchmark conditions and should **not** be interpreted as production accuracy or generalized performance across enterprise environments.

---

# 👩‍💻 Author

**Varshini V Poojary**

Computer Science & Information Security | CloudOps | SDET | AI/GraphRAG

GitHub:

https://github.com/varsh-28

---

⭐ If you find the project useful, consider starring the repository.
