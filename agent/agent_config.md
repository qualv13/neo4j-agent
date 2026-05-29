# DrugPath — Aura Agent Configuration Guide

How to configure the **DrugPath** agent in the Neo4j Aura Agent UI.

**Prerequisites:** the ETL has run (`etl/01`–`05`), so the graph is loaded and the
`compound_embedding` vector index is active.

## Files in this folder

| File | Purpose |
|---|---|
| `system_prompt.txt` | The agent's system prompt |
| `tools/drug_interaction_checker.cypher` | Cypher template — Tool 1 |
| `tools/drug_repurposing_explorer.cypher` | Cypher template — Tool 2 |
| `tools/drug_profile_lookup.cypher` | Cypher template — Tool 3 |
| `tools/find_similar_drugs.md` | Similarity Search tool — Tool 4 (UI-configured) |

---

## Step 1 — Open Aura Agent

1. Go to https://console.neo4j.io
2. Click your AuraDB instance.
3. In the left menu click **"Aura Agent"** (or the robot icon).
4. Click **"Create Agent"**.

## Step 2 — Basic configuration

- **Agent Name:** `DrugPath`
- **Agent Instructions / System Prompt:** Paste the entire contents of
  [`system_prompt.txt`](./system_prompt.txt) into the **"Agent Instructions"**
  / **"System Prompt"** field.

## Step 3 — Register the 4 tools

Add each tool below via **"Add Tool"** in the agent configuration.

### Tool 1 — `drug_interaction_checker` (Cypher Template)

- **Type:** Cypher Template
- **Name:** `drug_interaction_checker`
- **Description:** Copy the description from the header of
  [`tools/drug_interaction_checker.cypher`](./tools/drug_interaction_checker.cypher).
- **Cypher Query:** Paste the query body from that file (everything below the
  header comment block).
- **Parameters:**
  - `drug1_name` (String) — name of the first drug
  - `drug2_name` (String) — name of the second drug

### Tool 2 — `drug_repurposing_explorer` (Cypher Template)

- **Type:** Cypher Template
- **Name:** `drug_repurposing_explorer`
- **Description:** Copy the description from the header of
  [`tools/drug_repurposing_explorer.cypher`](./tools/drug_repurposing_explorer.cypher).
- **Cypher Query:** Paste the query body from that file.
- **Parameters:**
  - `disease_name` (String) — name of the disease (e.g. "Alzheimer",
    "breast cancer", "type 2 diabetes")

### Tool 3 — `drug_profile_lookup` (Cypher Template)

- **Type:** Cypher Template
- **Name:** `drug_profile_lookup`
- **Description:** Copy the description from the header of
  [`tools/drug_profile_lookup.cypher`](./tools/drug_profile_lookup.cypher).
- **Cypher Query:** Paste the query body from that file.
- **Parameters:**
  - `drug_name` (String) — name of the drug (e.g. "aspirin", "warfarin",
    "metformin")

### Tool 4 — `find_similar_drugs` (Similarity Search)

This is the built-in Aura Agent **Similarity Search** tool — it is configured
through UI fields, not a raw Cypher query. See
[`tools/find_similar_drugs.md`](./tools/find_similar_drugs.md) for full detail.

- **Type:** Similarity Search
- **Name:** `find_similar_drugs`
- **Description / Prompt:** Use the description and prompt text from the
  markdown file.
- **UI fields:**
  - **Index:** `compound_embedding`
  - **Top K:** `5`
  - **Embedding provider:** `OpenAI`
  - **Embedding model:** `text-embedding-3-small`
  - **Vector Dimensions:** `1536`
  - **Return connected graph data:** on (optional)
  - **Traversal (Natural language):** "Return the name and identifier of each matching Compound."

> **Must match the ETL.** `etl/04` writes OpenAI `text-embedding-3-small`
> (1536-dim) vectors; this dialog must use the same provider, model and
> dimensions or the results are meaningless. See
> [`tools/find_similar_drugs.md`](./tools/find_similar_drugs.md).

## Step 4 — Save and test

Click **"Update Agent"**, then test with
[`../tests/demo_scenarios.md`](../tests/demo_scenarios.md), for example:

- "Can I take warfarin and aspirin together?" (Tool 1)
- "What existing drugs might work for Alzheimer's disease?" (Tool 2)
- "Give me a complete profile of metformin." (Tool 3)
- "What drugs are similar to metformin in terms of how they work?" (Tool 4)

## Step 5 — Publish (optional, but earns bonus points)

1. In the agent configuration click **"External Access"**.
2. Enable **"Enable Public Access"**.
3. Copy the endpoint URL and include it in your hackathon submission.
