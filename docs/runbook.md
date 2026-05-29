# DrugPath Operator Runbook

Zero to a working agent. This guide takes you from a fresh machine to a tested,
submittable DrugPath agent running on Neo4j Aura. Commands use **Windows
PowerShell** syntax throughout.

Estimated time: 1–2 hours (most of it is the embeddings step and the Aura Agent
UI configuration).

---

## (a) Prerequisites

- [ ] **Python 3.12** installed and on `PATH`. Verify:
  ```powershell
  python --version
  ```
  Expect `Python 3.12.x`. If `python` is not found, install from
  [python.org](https://www.python.org/downloads/) and re-open PowerShell.
- [ ] A **Neo4j Aura Free** account — sign up at
  [console.neo4j.io](https://console.neo4j.io). Free, no credit card required.
- [ ] An **OpenAI API key** ([platform.openai.com](https://platform.openai.com)) —
  used only by `etl/04` to embed compounds for similarity search (a fraction of a
  cent). The agent itself needs no key; Aura manages the query-side embeddings.

---

## (b) Environment setup

All commands run from the repository root (`H:\Projects\neo4j agent`).

1. **Create a virtual environment:**
   ```powershell
   python -m venv drugpath-env
   ```

2. **Activate it:**
   ```powershell
   drugpath-env\Scripts\Activate.ps1
   ```
   Your prompt should now be prefixed with `(drugpath-env)`.

   > If activation is blocked by execution policy, run once for this session:
   > ```powershell
   > Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
   > ```

3. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

4. **Create your `.env` file from the template:**
   ```powershell
   Copy-Item .env.example .env
   ```
   Then open `.env` and fill in the values from your Aura instance (next step):
   ```powershell
   notepad .env
   ```
   Set `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` and `OPENAI_API_KEY`.

   - [ ] venv created and activated
   - [ ] `pip install -r requirements.txt` succeeded
   - [ ] `.env` created and filled in

---

## (c) Create the AuraDB Free instance

See guide **section 4** for screenshots and full detail.

1. Go to [console.neo4j.io](https://console.neo4j.io).
2. Click **New Instance** → choose **AuraDB Free**.
3. Pick a region close to you (e.g. `eu-west-1` for Poland).
4. **Download the credentials file when prompted** — this is your only chance to
   see the password. It contains:
   - `NEO4J_URI` (e.g. `neo4j+s://xxxx.databases.neo4j.io`)
   - `NEO4J_USERNAME` (default `neo4j`)
   - `NEO4J_PASSWORD`
5. Copy those three values into your `.env` file.

### Capacity limit — read this before loading

> **AuraDB Free caps at 200,000 nodes and 400,000 relationships.**
> Hetionet has ~47k nodes (fine) but **2.25M relationships (far over the limit)**.

**Strategy:** load **all nodes**, but **filter relationships to the most
demo-relevant metaedges only**. The ETL does this automatically — `01_download_hetionet.py`
keeps only:

| Metaedge | Relationship | Why it matters |
|---|---|---|
| `CbG` | `BINDS_GENE` | drug → molecular target |
| `CdG` | `DOWNREGULATES_GENE` | drug lowers gene expression |
| `CuG` | `UPREGULATES_GENE` | drug raises gene expression |
| `CtD` | `TREATS` | drug treats disease |
| `CpD` | `PALLIATES` | drug eases symptoms |
| `CcSE` | `CAUSES_SIDE_EFFECT` | adverse effects |
| `GpPW` | `PARTICIPATES_IN` | gene → pathway |
| `DaG` | `ASSOCIATES_WITH` | gene ↔ disease (the repurposing edge) |
| `DlA` | `LOCALIZES_TO` | disease → anatomy |
| `PCiC` | `INCLUDES` | drug class membership |

This lands at ~293k relationships, comfortably under the cap. If you add more
metaedges and exceed 400k, drop the regulation edges (`CdG`/`CuG`) first and
re-run `03_load_edges.py`.

- [ ] AuraDB Free instance created
- [ ] Credentials copied into `.env`

---

## (d) Run the ETL (in order)

Make sure your venv is active and `.env` is filled in. Run each script from the
repo root.

1. **Download + filter Hetionet:**
   ```powershell
   python etl/01_download_hetionet.py
   ```
   Downloads nodes and edges into `data/`, prints counts, and writes the
   filtered `data/edges_filtered.tsv` and `data/nodes_clean.tsv`.

2. **Load nodes:**
   ```powershell
   python etl/02_load_nodes.py
   ```
   Creates indexes and loads all node types in batches.

3. **Load relationships:**
   ```powershell
   python etl/03_load_edges.py
   ```
   Loads only the filtered metaedges. This is the longest pure-DB step.

4. **Generate embeddings (for similarity search):**
   ```powershell
   python etl/04_generate_embeddings.py
   ```
   Embeds all compounds with OpenAI `text-embedding-3-small` and builds the
   `compound_embedding` vector index (1536 dims). When you later configure the
   `find_similar_drugs` tool, set its model and dimensions to match — see
   [`agent/tools/find_similar_drugs.md`](../agent/tools/find_similar_drugs.md).

5. **Verify everything loaded:**
   ```powershell
   python etl/05_verify.py
   ```
   Prints node/relationship counts and runs the metformin repurposing query.
   Fix any failures before configuring the agent.

   - [ ] `01` downloaded + filtered
   - [ ] `02` nodes loaded
   - [ ] `03` relationships loaded
   - [ ] `04` embeddings generated, vector index active
   - [ ] `05` verification passed

---

## (e) Configure the Aura Agent

Full detail and the exact field contents live in
[`agent/agent_config.md`](../agent/agent_config.md). High-level flow:

1. In [console.neo4j.io](https://console.neo4j.io), open your AuraDB instance and
   click **Aura Agent** → **Create Agent**.
2. **Agent Name:** `DrugPath`.
3. **System Prompt / Agent Instructions:** paste the contents of
   [`agent/system_prompt.txt`](../agent/system_prompt.txt).
4. **Add the four tools** (Cypher and config in `agent/tools/`):
   - `drug_interaction_checker` — Cypher Template
   - `drug_repurposing_explorer` — Cypher Template
   - `drug_profile_lookup` — Cypher Template
   - `find_similar_drugs` — Similarity Search (see
     [`agent/tools/find_similar_drugs.md`](../agent/tools/find_similar_drugs.md);
     index `compound_embedding`, label `Compound`, property `embedding`)
5. Click **Update Agent**.
6. **(Optional, +points)** Open **External Access** → enable **Public Access** →
   copy the endpoint URL for your submission.

- [ ] Agent created and named `DrugPath`
- [ ] System prompt pasted
- [ ] All 4 tools added
- [ ] (Optional) public endpoint enabled and URL saved

---

## (f) Test the agent

Open the agent chat in Aura Console and walk through
[`tests/demo_scenarios.md`](../tests/demo_scenarios.md). Confirm each tool fires
and the answers explain the **mechanism** (not just yes/no). Don't skip the drug
repurposing scenario — that's the WOW moment for judges.

- [ ] Interaction checker scenario works
- [ ] Repurposing scenario works (the WOW moment)
- [ ] Profile lookup works
- [ ] Similarity search works
- [ ] Multi-hop reasoning works

---

## (g) Submit

1. Take the two required screenshots:
   - Graph schema: in Neo4j Browser run `CALL db.schema.visualization()`.
   - The agent answering a question in Aura Console (use the repurposing demo).
2. Open [`submission/hackathon_post.md`](../submission/hackathon_post.md), paste
   in your screenshots and (optional) public endpoint URL.
3. Post it to [community.neo4j.com](https://community.neo4j.com) with the title
   **DrugPath Agent**.

- [ ] Schema screenshot captured
- [ ] Agent-in-action screenshot captured
- [ ] Post submitted to community.neo4j.com

---

*Disclaimer: DrugPath is an educational and research tool. It does not provide
medical advice. Always consult a qualified healthcare professional for medical
decisions.*
