# find_similar_drugs (Similarity Search)

A built-in Aura Agent Similarity Search tool — configured through the UI, not
Cypher. Finds drugs whose embeddings are close to the query, for "alternatives
to X" / "drugs like X" questions.

**Description (paste into the tool):**

> Find drugs similar to a given drug based on the semantic similarity of their
> descriptions and mechanisms. Use for alternatives or "drugs like X" questions.
> Do not use for specific drug interactions or disease lookups.

**UI fields:**

| Field | Value |
|---|---|
| Index | `compound_embedding` |
| Top K | `5` |
| Embedding provider | `OpenAI` |
| Embedding model | `text-embedding-3-small` |
| Vector dimensions | `1536` |
| Return connected graph data | on (optional) |

The provider, model and dimensions must match what `etl/04` wrote (OpenAI
`text-embedding-3-small`, 1536-d). Aura Agent generates the query embedding with
its own managed OpenAI access, so no key is needed here — but if these settings
don't match the stored vectors the results are meaningless.
