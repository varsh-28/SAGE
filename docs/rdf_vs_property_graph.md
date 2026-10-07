# RDF triple store vs property graph, from this project's queries

The RDF side below is what `opsgraph/queries.py` runs. The Cypher side is a hand-written equivalent for
a Neo4j model with these labels and relationship types. It has NOT been executed in this repository.

Property-graph model:
`(:Incident)-[:AFFECTS_SERVICE]->(:Service)`, `(:Incident)-[:HAS_ROOT_CAUSE]->(:RootCause)`,
`(:RootCause)-[:RESOLVED_BY]->(:Runbook)`, `(:Service)-[:DEPENDS_ON]->(:Service)`.

## 1. Incidents sharing a root cause with INC-0042

SPARQL
```sparql
SELECT DISTINCT ?other WHERE {
  data:INC-0042 ops:hasRootCause ?rc .
  ?other ops:hasRootCause ?rc .
  FILTER(?other != data:INC-0042)
}
```
Cypher
```cypher
MATCH (:Incident {id: 'INC-0042'})-[:HAS_ROOT_CAUSE]->(rc)<-[:HAS_ROOT_CAUSE]-(other:Incident)
WHERE other.id <> 'INC-0042'
RETURN DISTINCT other.id
```

## 2. Services depending directly on payment-service

SPARQL
```sparql
SELECT DISTINCT ?d WHERE { ?d ops:dependsOn data:payment-service }
```
Cypher
```cypher
MATCH (d:Service)-[:DEPENDS_ON]->(:Service {id: 'payment-service'})
RETURN DISTINCT d.id
```

## 3. Incidents on services that depend on payment-service

SPARQL
```sparql
SELECT DISTINCT ?i WHERE {
  ?d ops:dependsOn data:payment-service .
  ?i ops:affectsService ?d .
}
```
Cypher
```cypher
MATCH (i:Incident)-[:AFFECTS_SERVICE]->(:Service)-[:DEPENDS_ON]->(:Service {id: 'payment-service'})
RETURN DISTINCT i.id
```

## 4. Transitive dependents (not implemented in the project; shows a difference)

SPARQL property path
```sparql
SELECT DISTINCT ?d WHERE { ?d ops:dependsOn+ data:cache-layer }
```
Cypher variable-length pattern
```cypher
MATCH (d:Service)-[:DEPENDS_ON*1..]->(:Service {id: 'cache-layer'})
RETURN DISTINCT d.id
```

## Trade-offs observed

| Concern | RDF + OWL/SKOS/SHACL | Property graph (Neo4j) |
|---|---|---|
| Schema and validation | Ontology and SHACL shapes are standard, portable, machine-checkable. This project's CI gates on them. | Constraints are product-specific. No standard shape language. |
| Vocabularies | SKOS gives a standard way to model the symptom thesaurus (prefLabel, altLabel, broader). | Possible, but you design the convention yourself. |
| Edge attributes | Needs reification or RDF-star to put properties on a relationship. | Relationships carry properties natively. |
| Path queries | SPARQL property paths (`+`, `*`). | Variable-length patterns and graph algorithms library. |
| Interchange and federation | Global IRIs, standard serialisations, SPARQL federation. | Export and import are product-specific. |
| Developer ergonomics | Steeper learning curve. | Pattern syntax reads closer to the whiteboard. |

Conclusion for this project: RDF fits because the value is in shared, validated, standards-based
semantics. A property graph would be preferable if relationships needed rich attributes and the
workload were mostly traversal.
