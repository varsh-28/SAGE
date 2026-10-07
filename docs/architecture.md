# Architecture

```mermaid
flowchart LR
    G[generate_data.py<br/>synthetic records + gold Qs] --> D[(dataset.json)]
    D --> B[graph_builder.py]
    O[ontology/opsgraph.ttl<br/>OWL + SKOS] --> B
    B --> R[(RDF graph<br/>rdflib)]
    S[ontology/shapes.ttl<br/>SHACL] --> V[validate.py]
    R --> V
    D --> E[retrieval.py<br/>vector index]
    Q[question] --> VEC[vector-only RAG<br/>top-k records]
    E --> VEC
    Q --> L[entity linking<br/>INC id / service name<br/>vector top-1 fallback]
    E --> L
    L --> RT[intent router<br/>keyword rules]
    RT --> SP[templated SPARQL<br/>queries.py]
    R --> SP
    SP --> CTX[graph context + facts]
    VEC --> ANS[answer<br/>optional Ollama LLM]
    CTX --> ANS
    ANS --> API[FastAPI]
    VEC --> EV[evaluate.py<br/>recall / precision]
    CTX --> EV
```

## Two retrieval paths over the same records

| | Vector-only RAG | GraphRAG |
|---|---|---|
| Unit retrieved | Whole incident record as text | Entities and relations via SPARQL |
| Finds | Records textually similar to the question | Records connected by explicit edges |
| Fails on | "Which incidents share this root cause?" (the other incidents do not mention the question's text) | Questions the intent router does not recognise |

## Design decisions

- **Gold answers are computed from raw records in plain Python**, not from the graph. A correct SPARQL query has to reproduce them independently. `tests/test_queries.py` asserts this.
- **Entity ids are validated before substitution into SPARQL** (`queries._iri`), so question text cannot inject query syntax.
- **SHACL is a gate**: CI fails if the generated graph stops conforming (`opsgraph.cli all --check`).
- **Backend fallback**: sentence-transformers if installed, otherwise TF-IDF. The backend used is written to `reports/results.json`.

## Known limitations

1. Intent routing is keyword rules. Paraphrased questions can be misrouted.
2. SPARQL is templated. LLM text-to-SPARQL is not implemented.
3. The graph path gets exact-id entity linking that the vector baseline does not.
4. Data is synthetic, so the comparison is controlled, not a production result.
5. Gold questions are template-generated. Add hand-written ones in `data/gold_manual.json`.
