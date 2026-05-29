# DrugPath Demo Scenarios

Test scripts for verifying the agent and for live demos to judges. Each scenario
lists the **question to ask**, the **tool it exercises**, and the **expected
answer shape** — what a good response should contain.

Golden rule for every answer: DrugPath must explain the **mechanism** and show
the **reasoning path** through the graph, not just return a flat result.

> Run these in the Aura Console agent chat after completing the runbook
> (`docs/runbook.md`).

---

## Demo 1 — Drug interaction checking

**Tool:** `drug_interaction_checker`

> **Naming note (validated against the live DB):** Hetionet stores formal
> chemical names — there is **no "aspirin" node**; it's **"Acetylsalicylic acid"**.
> The system prompt instructs the agent to map common names automatically, so a
> judge can still type "aspirin." If you query the tool directly, use the formal
> name. The tool reports the molecular targets and pathways the two drugs share.

### Scenario 1a (English)
> "Can I take warfarin and aspirin together?"

**Expected answer shape (matches live data):**
- The agent maps *aspirin → Acetylsalicylic acid* and calls the tool.
- Reports **shared molecular targets: CYP2C19, CYP2C8, CYP2C9, ALB** and
  **shared pathways including Arachidonic acid metabolism**.
- Mechanism story: both are metabolized by the **CYP2C9** family (competition →
  altered warfarin clearance) and both bind albumin (**ALB**, protein-binding
  displacement → more free warfarin); aspirin's COX/arachidonic-acid effect adds
  antiplatelet action → **increased bleeding risk**.
- Includes the educational disclaimer.

### Scenario 1b (Polish)
> "Czy metformina wchodzi w interakcje z ibuprofenem?"

**Expected answer shape (matches live data):**
- Metformin and Ibuprofen share **no direct gene targets**, but share broad
  transport/metabolism pathways (SLC-mediated transmembrane transport,
  Metabolism). The agent should report this honestly (no strong shared target),
  optionally noting the known NSAID effect on renal clearance of metformin.
- Reports the absence of shared targets honestly rather than inventing a verdict.
  Disclaimer included.

---

## Demo 2 — Drug repurposing (THE WOW MOMENT)

**Tool:** `drug_repurposing_explorer`

> This is the headline demo. It answers a question that is **impossible in a flat
> table** — it requires a 3-hop traversal `Compound → Gene → Disease`. Lead with
> this one for judges.

> **Validated live results (so you know what to expect):**
> - **Breast cancer →** Cyclosporine, Pravastatin, Cabazitaxel, Vincristine,
>   Bosutinib, Nelfinavir, Acetaminophen… (connecting genes like CYP3A4, ABCB1,
>   TUBB3, EGFR, CDK2).
> - **Alzheimer's disease →** Dextromethorphan, Nicotine, Amitriptyline,
>   Nortriptyline, Imipramine, Chlorpromazine… (connecting genes like CHRNA4/7,
>   CHRNB2, HTR2A, BCHE, SLC6A4 — cholinergic & serotonergic targets, which is
>   biologically on-point for Alzheimer's).
> Disease names must be formal: use "Alzheimer's disease", "breast cancer".

### Scenario 2a (English)
> "What existing drugs might work for Alzheimer's disease?"

**Expected answer shape:**
- A ranked list of candidate drugs **approved for other conditions** whose
  molecular targets (Genes) **associate with** Alzheimer's.
- For each: the **connecting gene(s)** and what the drug is currently approved
  for.
- The explicit reasoning path:
  `Drug → [BINDS_GENE] → Gene → [ASSOCIATES_WITH] → Alzheimer's Disease`.
- A clear caveat that these are **hypotheses for researchers**, not proven
  treatments. Disclaimer included.

### Scenario 2b (English — second framing)
> "What drugs approved for other conditions could potentially treat breast cancer?"

**Expected answer shape:**
- Same structure as 2a, targeting breast cancer.
- Emphasizes that this answer **cannot be produced without the graph** — it
  crosses node types (`Compound`, `Gene`, `Disease`) in a single query.
- Names the connecting genes for each candidate.

---

## Demo 3 — Drug profile lookup

**Tool:** `drug_profile_lookup`

### Scenario 3a (English)
> "Give me a complete profile of metformin — what does it target, treat, and what are its side effects?"

**Expected answer shape (matches live data):**
- **Treats:** type 2 diabetes mellitus, polycystic ovary syndrome, metabolic
  syndrome X.
- **Molecular targets:** mitochondrial **Complex I** subunits — NDUFA11, NDUFS7,
  ND1, ND2, ND3, etc. (This *is* metformin's real mechanism: Complex I
  inhibition → raised AMP/ATP → AMPK activation. The graph stores the direct
  binding targets, so don't expect a literal "AMPK" node here.)
- **Side effects:** abdominal distension/pain, acidosis, anorexia, asthenia…
- **Biological pathways:** Oxidative phosphorylation, Respiratory electron
  transport, the citric acid (TCA) cycle, Metabolism.
- **Drug class:** Biguanides.
- Presented as a structured profile assembled from graph relationships.

### Scenario 3b (English)
> "What are the molecular targets of ibuprofen?"

**Expected answer shape (matches live data):**
- Gene targets returned by the graph: **CYP2C9, CYP2C8, CYP2C19** (metabolism),
  **ALB** (albumin binding), and transporters **ABCC4, SLCO2B1, CFTR, FABP2**.
- Note: Hetionet's `BINDS_GENE` set here reflects metabolism/transport/binding
  partners rather than the pharmacodynamic COX targets — the agent should report
  what the graph holds and can add the well-known NSAID/COX context as background.
- **Class:** Nonsteroidal Anti-inflammatory Compounds; **palliates:**
  osteoarthritis; pathways include Hemostasis / Platelet activation.

---

## Demo 4 — Similar drugs (similarity search)

**Tool:** `find_similar_drugs`

### Scenario 4a (English)
> "What drugs are similar to metformin in terms of how they work?"

**Expected answer shape:**
- A list of pharmacologically similar compounds returned by **vector search**
  on the `compound_embedding` index.
- Each result names the drug; ideally a one-line note on why it's similar
  (shared class / mechanism).
- Should NOT invoke the interaction or disease tools — purely similarity.

### Scenario 4b (English)
> "Find me alternatives to warfarin for anticoagulation."

**Expected answer shape:**
- Semantically similar anticoagulant-adjacent compounds from the vector index.
- Framed as "similar by mechanism/description," with the disclaimer.

---

## Demo 5 — Multi-hop reasoning (Text2Cypher, if configured)

**Tool:** Text2Cypher / multi-hop (only if you enabled it)

### Scenario 5a (English)
> "Which drugs target genes associated with type 2 diabetes AND also cause nausea as a side effect?"

**Expected answer shape:**
- A combined 3-hop result:
  `Compound → [BINDS_GENE] → Gene → [ASSOCIATES_WITH] → type 2 diabetes`
  intersected with
  `Compound → [CAUSES_SIDE_EFFECT] → nausea`.
- Lists drugs satisfying **both** conditions, demonstrating the graph composing
  two independent traversals in one query.
- Disclaimer included.

---

## Quick checklist for a live demo

- [ ] Demo 1a — interaction checker (warfarin + aspirin)
- [ ] Demo 2a — repurposing for Alzheimer's (**lead with this — WOW moment**)
- [ ] Demo 3a — metformin full profile
- [ ] Demo 4a — drugs similar to metformin
- [ ] Demo 5a — multi-hop (if Text2Cypher configured)

*Disclaimer: DrugPath is an educational and research tool. It does not provide
medical advice. Always consult a qualified healthcare professional for medical
decisions.*
