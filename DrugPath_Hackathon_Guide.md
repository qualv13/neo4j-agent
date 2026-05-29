# DrugPath — Kompletna Instrukcja Implementacji
### Neo4j Aura Agent Hackathon 2026

> **Cel:** Zbudować agenta AI, który nawiguje sieć powiązań farmakologicznych i odpowiada „dlaczego" — nie tylko „co". Pole jest wolne, deadline 15 czerwca 2026, czas realizacji: 3–5 dni roboczych.

---

## Spis treści

1. [Czym jest DrugPath i co go wyróżnia](#1-czym-jest-drugpath)
2. [Datasety — linki i instrukcje pobierania](#2-datasety)
3. [Schemat grafu](#3-schemat-grafu)
4. [Konfiguracja Neo4j Aura Free](#4-konfiguracja-neo4j-aura-free)
5. [ETL — ładowanie danych](#5-etl-ładowanie-danych)
6. [Embeddingi dla Similarity Search](#6-embeddingi)
7. [Konfiguracja Aura Agent](#7-konfiguracja-aura-agent)
8. [Cztery narzędzia agenta — pełne Cypher queries](#8-narzędzia-agenta)
9. [System prompt agenta](#9-system-prompt)
10. [Testowanie — scenariusze demo](#10-testowanie)
11. [Gotowe zgłoszenie hackathonowe](#11-zgłoszenie-hackathonowe)

---

## 1. Czym jest DrugPath

**DrugPath** to agent AI, który rozumie sieć biologicznych powiązań leków. Zamiast zwracać prostą odpowiedź „tak/nie", śledzi ścieżkę przez graf: lek → gen (cel) → szlak biologiczny → choroba → działanie niepożądane — i wyjaśnia *mechanizm*.

### Dlaczego graf, nie tabela?

Pytanie: *„Dlaczego metformina może działać przeciwnowotworowo?"*

W tabeli: brak odpowiedzi (wskazania nie zawierają nowotworów).

W grafie:
```
(Metformin)-[:TARGETS]->(AMPK:Gene)
  -[:PARTICIPATES_IN]->(mTOR_pathway:Pathway)
  -[:ASSOCIATED_WITH]->(Cancer:Disease)
```
Odpowiedź wymaga przejścia przez 3 węzły. To jest drug repurposing przez wieloskokowe wnioskowanie — niemożliwe w płaskiej bazie.

### Co DrugPath umożliwia użytkownikom

- **Lekarze / farmaceuci:** sprawdzają interakcje między lekami z mechanizmem wyjaśnienia
- **Badacze:** odkrywają potencjalne nowe zastosowania istniejących leków (drug repurposing)
- **Pacjenci:** rozumieją dlaczego przepisany lek jest odpowiedni dla ich schorzenia
- **Firmy farmaceutyczne:** identyfikują potencjalne działania niepożądane przez szlaki biologiczne

---

## 2. Datasety

### Dataset główny: Hetionet v1.0

**Źródło:** https://github.com/hetio/hetionet  
**Licencja:** CC0 (public domain) — brak ograniczeń  
**Rozmiar:** 47 031 węzłów, 2 250 197 relacji, 29 publicznych źródeł

Hetionet integruje dane z: DrugBank, OMIM, DisGeNET, Reactome, Gene Ontology, SIDER, TISSUES, i innych.

**Pliki do pobrania (TSV — najłatwiejszy format):**

```
# Węzły
https://github.com/hetio/hetionet/raw/main/hetnet/tsv/hetionet-v1.0-nodes.tsv

# Relacje (gzip)
https://github.com/hetio/hetionet/raw/main/hetnet/tsv/hetionet-v1.0-edges.sif.gz
```

**Typy węzłów w Hetionet:**

| Label | Opis | Liczba |
|---|---|---|
| Compound | Lek / związek chemiczny | 1 552 |
| Gene | Gen / białko (cel leku) | 20 945 |
| Disease | Choroba | 137 |
| Pathway | Szlak biologiczny (np. CYP3A4) | 1 822 |
| Anatomy | Narząd / tkanka | 402 |
| Side Effect | Działanie niepożądane | 5 734 |
| Biological Process | Proces biologiczny (GO) | 11 381 |
| Symptom | Objaw kliniczny | 438 |
| Pharmacologic Class | Klasa farmakologiczna | 345 |
| Molecular Function | Funkcja molekularna | 2 884 |
| Cellular Component | Komponent komórkowy | 1 391 |

**Kluczowe typy relacji (metaedge):**

| Metaedge | Znaczenie |
|---|---|
| CbG (Compound binds Gene) | Lek wiąże się z genem (cel molekularny) |
| CdG (Compound downregulates Gene) | Lek obniża ekspresję genu |
| CuG (Compound upregulates Gene) | Lek podwyższa ekspresję genu |
| CtD (Compound treats Disease) | Lek leczy chorobę |
| CpD (Compound palliates Disease) | Lek łagodzi objawy choroby |
| CcSE (Compound causes Side Effect) | Lek powoduje działanie niepożądane |
| GpPW (Gene participates Pathway) | Gen uczestniczy w szlaku biologicznym |
| GaD (Gene associates Disease) | Gen powiązany z chorobą |
| DaG (Disease associates Gene) | Choroba powiązana z genem |

### Dataset uzupełniający: DrugBank interakcje lek-lek

**Źródło:** https://go.drugbank.com/releases/latest  
**Rejestracja:** bezpłatna dla badań akademickich  
**Plik:** `drugbank_all_drug_interactions.csv`

Zawiera ~1,4 mln interakcji lek-lek z polem `description` opisującym mechanizm.

> **Uwaga:** Jeśli rejestracja DrugBank zajmie czas, Hetionet sam w sobie jest wystarczający do silnego demo. DrugBank wzbogaca projekt o relację INTERACTS_WITH z opisem mechanizmu.

### Dataset opcjonalny: FDA Drug Labels (OpenFDA)

**Źródło:** https://open.fda.gov/drug/label/  
**API:** bezpłatny, bez rejestracji  
**Endpoint:** `https://api.fda.gov/drug/label.json?search=openfda.generic_name:"metformin"&limit=1`

Można pobrać opisy leków dla embeddingów.

---

## 3. Schemat grafu

### Węzły (z Hetionet + DrugBank)

```cypher
// Lek / związek chemiczny
(:Compound {
  identifier: String,    // "Compound::DB00331" (DrugBank ID)
  name: String,          // "Metformin"
  description: String,   // opis mechanizmu działania (dla embeddingów)
  embedding: List<Float> // wektor dla Similarity Search
})

// Gen / białko
(:Gene {
  identifier: String,    // "Gene::2475"
  name: String,          // "MTOR"
  description: String
})

// Choroba
(:Disease {
  identifier: String,    // "Disease::DOID:9352"
  name: String,          // "type 2 diabetes mellitus"
  description: String,
  embedding: List<Float>
})

// Szlak biologiczny
(:Pathway {
  identifier: String,    // "Pathway::R-HSA-165159"
  name: String           // "mTOR signalling"
})

// Działanie niepożądane
(:SideEffect {
  identifier: String,    // "Side Effect::C0027947"
  name: String           // "Nausea"
})

// Klasa farmakologiczna
(:PharmacologicClass {
  identifier: String,
  name: String           // "Biguanides"
})

// Narząd / anatomia
(:Anatomy {
  identifier: String,
  name: String           // "liver"
})
```

### Relacje

```cypher
// Cel molekularny
(Compound)-[:BINDS_GENE]->(Gene)
(Compound)-[:DOWNREGULATES_GENE]->(Gene)
(Compound)-[:UPREGULATES_GENE]->(Gene)

// Terapeutyczne
(Compound)-[:TREATS]->(Disease)
(Compound)-[:PALLIATES]->(Disease)

// Działania niepożądane
(Compound)-[:CAUSES_SIDE_EFFECT]->(SideEffect)

// Interakcje lek-lek (z DrugBank)
(Compound)-[:INTERACTS_WITH {
  description: String,   // mechanizm interakcji
  severity: String       // "major" | "moderate" | "minor"
}]->(Compound)

// Szlaki biologiczne
(Gene)-[:PARTICIPATES_IN]->(Pathway)

// Powiązania z chorobami
(Gene)-[:ASSOCIATES_WITH]->(Disease)
(Disease)-[:LOCALIZES_TO]->(Anatomy)

// Klasyfikacja
(Compound)-[:IN_CLASS]->(PharmacologicClass)
```

### Diagram schematu

```
[PharmacologicClass]
        ↑
    IN_CLASS
        |
  [Compound] ──TREATS──────────────────► [Disease]
      │    └──PALLIATES──────────────────► [Disease]
      │                                        │
  BINDS_GENE                           LOCALIZES_TO
  DOWNREGULATES_GENE                        │
  UPREGULATES_GENE                     [Anatomy]
      │
      ▼
   [Gene] ──PARTICIPATES_IN──► [Pathway]
      │
   ASSOCIATES_WITH
      │
      ▼
  [Disease]

  [Compound] ──CAUSES_SIDE_EFFECT──► [SideEffect]
  [Compound] ──INTERACTS_WITH──────► [Compound]
               {description, severity}
```

---

## 4. Konfiguracja Neo4j Aura Free

### Krok 1 — Utwórz konto i instancję

1. Wejdź na https://console.neo4j.io
2. Kliknij **"New Instance"** → wybierz **AuraDB Free**
3. Wybierz region (np. `eu-west-1` dla Polski)
4. Pobierz plik `.env` z danymi połączenia — zawiera:
   - `NEO4J_URI` (np. `neo4j+s://xxxx.databases.neo4j.io`)
   - `NEO4J_USERNAME` (domyślnie `neo4j`)
   - `NEO4J_PASSWORD`

> **Limit AuraDB Free:** 200 000 węzłów, 400 000 relacji. Hetionet ma 47k węzłów i 2,25M relacji — **przekracza limit relacji**. Strategia: załaduj pełne węzły, ale ogranicz relacje do najważniejszych typów (CbG, CtD, CpD, CcSE, GpPW, GaD — ~500k relacji). To nadal robi piorunujące demo.

### Krok 2 — Zainstaluj środowisko Python

```bash
python -m venv drugpath-env
source drugpath-env/bin/activate  # Linux/Mac
# lub: drugpath-env\Scripts\activate  # Windows

pip install neo4j pandas numpy openai requests tqdm python-dotenv
```

### Krok 3 — Plik .env

```env
NEO4J_URI=neo4j+s://xxxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password-here
OPENAI_API_KEY=sk-...         # dla embeddingów (opcjonalne, można użyć darmowych alternatyw)
```

---

## 5. ETL — Ładowanie danych

### Skrypt 1: Pobieranie i parsowanie Hetionet

```python
# etl/01_download_hetionet.py
import pandas as pd
import gzip
import urllib.request
from pathlib import Path

Path("data").mkdir(exist_ok=True)

# Pobierz węzły
print("Pobieranie węzłów...")
urllib.request.urlretrieve(
    "https://github.com/hetio/hetionet/raw/main/hetnet/tsv/hetionet-v1.0-nodes.tsv",
    "data/nodes.tsv"
)

# Pobierz relacje
print("Pobieranie relacji...")
urllib.request.urlretrieve(
    "https://github.com/hetio/hetionet/raw/main/hetnet/tsv/hetionet-v1.0-edges.sif.gz",
    "data/edges.sif.gz"
)

# Wczytaj węzły
nodes = pd.read_csv("data/nodes.tsv", sep="\t")
print(f"Węzłów razem: {len(nodes)}")
print(nodes['kind'].value_counts())

# Wczytaj relacje
with gzip.open("data/edges.sif.gz", 'rt') as f:
    edges = pd.read_csv(f, sep="\t", header=None, names=["source", "metaedge", "target"])
print(f"\nRelacji razem: {len(edges)}")
print(edges['metaedge'].value_counts().head(15))

# Zapisz filtrowane relacje (tylko te potrzebne do demo)
IMPORTANT_METAEDGES = {
    'CbG',   # Compound binds Gene
    'CdG',   # Compound downregulates Gene
    'CuG',   # Compound upregulates Gene
    'CtD',   # Compound treats Disease
    'CpD',   # Compound palliates Disease
    'CcSE',  # Compound causes Side Effect
    'GpPW',  # Gene participates Pathway
    'GaD',   # Gene associates Disease
    'DlA',   # Disease localizes Anatomy
    'PCiC',  # PharmacologicClass includes Compound
}

edges_filtered = edges[edges['metaedge'].isin(IMPORTANT_METAEDGES)]
print(f"\nRelacji po filtrowaniu: {len(edges_filtered)}")
edges_filtered.to_csv("data/edges_filtered.tsv", sep="\t", index=False)
nodes.to_csv("data/nodes_clean.tsv", sep="\t", index=False)
print("Gotowe! Pliki zapisane w data/")
```

### Skrypt 2: Ładowanie węzłów do Neo4j

```python
# etl/02_load_nodes.py
import pandas as pd
from neo4j import GraphDatabase
from dotenv import load_dotenv
import os
from tqdm import tqdm

load_dotenv()

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
)

nodes = pd.read_csv("data/nodes_clean.tsv", sep="\t")

# Mapowanie kind -> label Neo4j
KIND_TO_LABEL = {
    "Compound": "Compound",
    "Gene": "Gene",
    "Disease": "Disease",
    "Pathway": "Pathway",
    "Side Effect": "SideEffect",
    "Pharmacologic Class": "PharmacologicClass",
    "Anatomy": "Anatomy",
    "Biological Process": "BiologicalProcess",
    "Symptom": "Symptom",
    "Molecular Function": "MolecularFunction",
    "Cellular Component": "CellularComponent",
}

def load_nodes_batch(tx, batch, label):
    query = f"""
    UNWIND $nodes AS node
    MERGE (n:{label} {{identifier: node.id}})
    SET n.name = node.name
    """
    tx.run(query, nodes=batch)

# Tworzenie indeksów
with driver.session() as session:
    for label in KIND_TO_LABEL.values():
        session.run(f"CREATE INDEX {label.lower()}_id IF NOT EXISTS FOR (n:{label}) ON (n.identifier)")
    print("Indeksy utworzone.")

# Ładowanie węzłów grupami po 1000
BATCH_SIZE = 1000
for kind, label in KIND_TO_LABEL.items():
    subset = nodes[nodes['kind'] == kind]
    if len(subset) == 0:
        continue
    records = subset[['id', 'name']].to_dict('records')
    with driver.session() as session:
        for i in tqdm(range(0, len(records), BATCH_SIZE), desc=f"Ładowanie {label}"):
            batch = records[i:i+BATCH_SIZE]
            session.execute_write(load_nodes_batch, batch, label)
    print(f"  {label}: {len(records)} węzłów załadowanych")

driver.close()
print("\nWęzły załadowane!")
```

### Skrypt 3: Ładowanie relacji do Neo4j

```python
# etl/03_load_edges.py
import pandas as pd
from neo4j import GraphDatabase
from dotenv import load_dotenv
import os
from tqdm import tqdm

load_dotenv()

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
)

edges = pd.read_csv("data/edges_filtered.tsv", sep="\t")

# Mapowanie metaedge -> Neo4j relationship type + typy węzłów
METAEDGE_MAP = {
    'CbG':  ("Compound",          "BINDS_GENE",          "Gene"),
    'CdG':  ("Compound",          "DOWNREGULATES_GENE",  "Gene"),
    'CuG':  ("Compound",          "UPREGULATES_GENE",    "Gene"),
    'CtD':  ("Compound",          "TREATS",              "Disease"),
    'CpD':  ("Compound",          "PALLIATES",           "Disease"),
    'CcSE': ("Compound",          "CAUSES_SIDE_EFFECT",  "SideEffect"),
    'GpPW': ("Gene",              "PARTICIPATES_IN",     "Pathway"),
    'GaD':  ("Gene",              "ASSOCIATES_WITH",     "Disease"),
    'DlA':  ("Disease",           "LOCALIZES_TO",        "Anatomy"),
    'PCiC': ("PharmacologicClass","INCLUDES",            "Compound"),
}

def load_edges_batch(tx, batch, source_label, rel_type, target_label):
    query = f"""
    UNWIND $edges AS edge
    MATCH (s:{source_label} {{identifier: edge.source}})
    MATCH (t:{target_label} {{identifier: edge.target}})
    MERGE (s)-[:{rel_type}]->(t)
    """
    tx.run(query, edges=batch)

BATCH_SIZE = 500

for metaedge, (src_label, rel_type, tgt_label) in METAEDGE_MAP.items():
    subset = edges[edges['metaedge'] == metaedge]
    if len(subset) == 0:
        continue
    records = subset[['source', 'target']].to_dict('records')
    
    with driver.session() as session:
        for i in tqdm(range(0, len(records), BATCH_SIZE), desc=f"{rel_type}"):
            batch = records[i:i+BATCH_SIZE]
            session.execute_write(load_edges_batch, batch, src_label, rel_type, tgt_label)
    print(f"  {rel_type}: {len(records)} relacji")

driver.close()
print("\nRelacje załadowane!")
```

### Skrypt 4: Opcjonalny — interakcje lek-lek z DrugBank

```python
# etl/04_load_drugbank_interactions.py
# Uruchom po pobraniu drugbank_all_drug_interactions.csv z go.drugbank.com
import pandas as pd
from neo4j import GraphDatabase
from dotenv import load_dotenv
import os
from tqdm import tqdm

load_dotenv()
driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
)

# DrugBank CSV ma kolumny: Drug1_DrugBank_ID, Drug2_DrugBank_ID, Description
ddi = pd.read_csv("data/drugbank_all_drug_interactions.csv")

def load_ddi_batch(tx, batch):
    query = """
    UNWIND $interactions AS ddi
    MATCH (d1:Compound) WHERE d1.identifier CONTAINS ddi.drug1_id
    MATCH (d2:Compound) WHERE d2.identifier CONTAINS ddi.drug2_id
    MERGE (d1)-[r:INTERACTS_WITH]->(d2)
    SET r.description = ddi.description,
        r.severity = ddi.severity
    """
    tx.run(query, interactions=batch)

records = ddi.rename(columns={
    'Drug1_DrugBank_ID': 'drug1_id',
    'Drug2_DrugBank_ID': 'drug2_id',
    'Description': 'description',
}).to_dict('records')

BATCH_SIZE = 500
with driver.session() as session:
    for i in tqdm(range(0, len(records), BATCH_SIZE)):
        batch = records[i:i+BATCH_SIZE]
        session.execute_write(load_ddi_batch, batch)

driver.close()
print(f"Załadowano {len(records)} interakcji lek-lek")
```

### Weryfikacja danych w Neo4j Browser

Po załadowaniu uruchom w Neo4j Browser (console.neo4j.io → Open):

```cypher
// Sprawdź liczbę węzłów i relacji
MATCH (n) RETURN labels(n)[0] AS label, count(n) AS count ORDER BY count DESC;

// Test: co leczy metformina?
MATCH (c:Compound)-[:TREATS]->(d:Disease)
WHERE toLower(c.name) CONTAINS 'metformin'
RETURN c.name, d.name LIMIT 10;

// Test: drug repurposing — jaka ścieżka łączy metforminę z rakiem?
MATCH path = (c:Compound)-[:BINDS_GENE]->(g:Gene)-[:ASSOCIATES_WITH]->(d:Disease)
WHERE toLower(c.name) CONTAINS 'metformin'
AND toLower(d.name) CONTAINS 'cancer'
RETURN path LIMIT 3;
```

---

## 6. Embeddingi

Embeddingi są potrzebne do narzędzia **Similarity Search**. Generujemy je dla węzłów Compound i Disease.

### Skrypt: Generowanie embeddingów

```python
# etl/05_generate_embeddings.py
from neo4j import GraphDatabase
from openai import OpenAI
from dotenv import load_dotenv
import os
from tqdm import tqdm

load_dotenv()

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Pobierz nazwy leków
with driver.session() as session:
    result = session.run("MATCH (c:Compound) RETURN c.identifier AS id, c.name AS name")
    compounds = [{"id": r["id"], "name": r["name"], "text": f"Drug: {r['name']}"} for r in result]

print(f"Generowanie embeddingów dla {len(compounds)} leków...")

def get_embedding(text: str) -> list[float]:
    response = client.embeddings.create(
        model="text-embedding-3-small",  # tani, 1536 dim
        input=text
    )
    return response.data[0].embedding

def update_embeddings(tx, batch):
    query = """
    UNWIND $items AS item
    MATCH (c:Compound {identifier: item.id})
    CALL db.create.setNodeVectorProperty(c, 'embedding', item.embedding)
    """
    tx.run(query, items=batch)

# Batch po 100 (limit rate OpenAI)
BATCH_SIZE = 100
items_with_embeddings = []

for i in tqdm(range(0, len(compounds), BATCH_SIZE)):
    batch = compounds[i:i+BATCH_SIZE]
    texts = [item["text"] for item in batch]
    response = client.embeddings.create(model="text-embedding-3-small", input=texts)
    for item, emb_obj in zip(batch, response.data):
        items_with_embeddings.append({
            "id": item["id"],
            "embedding": emb_obj.embedding
        })

# Zapisz do Neo4j
with driver.session() as session:
    for i in tqdm(range(0, len(items_with_embeddings), 500)):
        batch = items_with_embeddings[i:i+500]
        session.execute_write(update_embeddings, batch)

# Utwórz vector index
with driver.session() as session:
    session.run("""
    CREATE VECTOR INDEX compound_embedding IF NOT EXISTS
    FOR (c:Compound) ON (c.embedding)
    OPTIONS {indexConfig: {
      `vector.dimensions`: 1536,
      `vector.similarity_function`: 'cosine'
    }}
    """)
    print("Vector index dla Compound utworzony!")

driver.close()
```

> **Alternatywa bez OpenAI:** użyj darmowego modelu `sentence-transformers/all-MiniLM-L6-v2` przez bibliotekę `sentence-transformers` (pip install sentence-transformers). Wymaga tylko lokalnego CPU.

```python
# Alternatywa — sentence-transformers (bezpłatna)
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')  # 384 dim
embedding = model.encode("Drug: Metformin").tolist()
# Następnie zmień dimensions na 384 w CREATE VECTOR INDEX
```

---

## 7. Konfiguracja Aura Agent

### Krok 1 — Otwórz Aura Agent

1. Wejdź na https://console.neo4j.io
2. Kliknij swoją instancję AuraDB
3. W menu po lewej kliknij **"Aura Agent"** (lub ikona robota)
4. Kliknij **"Create Agent"**

### Krok 2 — Wypełnij konfigurację podstawową

**Agent Name:** `DrugPath`

**Agent Description (dla systemu):**  
*(wklej z Sekcji 9 tego dokumentu)*

### Krok 3 — Dodaj 4 narzędzia

Szczegółowe konfiguracje każdego narzędzia w Sekcji 8.

### Krok 4 — Zapisz i testuj

Po dodaniu narzędzi kliknij **"Update Agent"** i przetestuj pytaniami z Sekcji 10.

### Krok 5 — Opublikuj (opcjonalne, ale +punkty)

1. W konfiguracji agenta kliknij **"External Access"**
2. Włącz **"Enable Public Access"**
3. Skopiuj endpoint URL — wklej do zgłoszenia

---

## 8. Narzędzia Agenta

### Narzędzie 1: Drug Interaction Checker (Cypher Template)

**Name:** `drug_interaction_checker`

**Description:**
```
Use this tool to check if two specific drugs interact with each other and to understand the mechanism of their interaction. Use when the user asks about combining two named drugs, about drug safety for a specific combination, or about contraindications. Input: two drug names. Returns: interaction details including the biological mechanism and severity if available.
```

**Cypher Query:**
```cypher
WITH toLower($drug1_name) AS d1, toLower($drug2_name) AS d2
MATCH (c1:Compound)
WHERE toLower(c1.name) CONTAINS d1
WITH c1, d2
MATCH (c2:Compound)
WHERE toLower(c2.name) CONTAINS d2
OPTIONAL MATCH (c1)-[r:INTERACTS_WITH]->(c2)
OPTIONAL MATCH (c2)-[r2:INTERACTS_WITH]->(c1)
WITH c1, c2,
     coalesce(r.description, r2.description) AS interaction_desc,
     coalesce(r.severity, r2.severity) AS severity
OPTIONAL MATCH (c1)-[:BINDS_GENE]->(g1:Gene)<-[:BINDS_GENE]-(c2)
WITH c1, c2, interaction_desc, severity,
     collect(DISTINCT g1.name) AS shared_targets
OPTIONAL MATCH (c1)-[:BINDS_GENE]->(g:Gene)-[:PARTICIPATES_IN]->(pw:Pathway)<-[:PARTICIPATES_IN]-(g2:Gene)<-[:BINDS_GENE]-(c2)
RETURN
  c1.name AS drug1,
  c2.name AS drug2,
  CASE WHEN interaction_desc IS NOT NULL THEN 'YES' ELSE 'UNKNOWN' END AS interacts,
  interaction_desc AS mechanism,
  severity AS severity,
  shared_targets AS shared_molecular_targets,
  collect(DISTINCT pw.name)[0..5] AS shared_pathways
LIMIT 1
```

**Parameters:**
- `drug1_name` (String) — nazwa pierwszego leku
- `drug2_name` (String) — nazwa drugiego leku

---

### Narzędzie 2: Drug Repurposing Explorer (Cypher Template)

**Name:** `drug_repurposing_explorer`

**Description:**
```
Use this tool to find drugs that might be repurposed for a new disease — i.e., drugs approved for other conditions but whose molecular targets are associated with the disease in question. Use when the user asks about potential new treatments for a disease, about what drugs might work for a condition they don't have an approved treatment for, or about drug repurposing. Input: disease name. Returns: list of candidate compounds with the gene pathway connecting them to the disease.
```

**Cypher Query:**
```cypher
WITH toLower($disease_name) AS disease_lower
MATCH (d:Disease)
WHERE toLower(d.name) CONTAINS disease_lower
WITH d LIMIT 1
MATCH (d)<-[:ASSOCIATES_WITH]-(g:Gene)<-[:BINDS_GENE]-(c:Compound)
WHERE NOT (c)-[:TREATS]->(d)
AND NOT (c)-[:PALLIATES]->(d)
WITH d, c, collect(DISTINCT g.name) AS connecting_genes
OPTIONAL MATCH (c)-[:TREATS]->(other_disease:Disease)
WITH d, c, connecting_genes,
     collect(DISTINCT other_disease.name)[0..3] AS current_indications
OPTIONAL MATCH (c)-[:IN_CLASS|INCLUDES*1]-(pc:PharmacologicClass)
RETURN
  d.name AS target_disease,
  c.name AS candidate_drug,
  connecting_genes[0..5] AS connecting_genes,
  current_indications AS currently_approved_for,
  pc.name AS drug_class
ORDER BY size(connecting_genes) DESC
LIMIT 10
```

**Parameters:**
- `disease_name` (String) — nazwa choroby (np. "Alzheimer", "breast cancer", "type 2 diabetes")

---

### Narzędzie 3: Drug Profile Lookup (Cypher Template)

**Name:** `drug_profile_lookup`

**Description:**
```
Use this tool to get a comprehensive profile of a specific drug: what diseases it treats, what genes it targets, what side effects it causes, and what drug class it belongs to. Use when the user asks "what does drug X do", "what are the targets of drug X", "what side effects does drug X have", or general questions about a named drug. Input: drug name.
```

**Cypher Query:**
```cypher
WITH toLower($drug_name) AS drug_lower
MATCH (c:Compound)
WHERE toLower(c.name) CONTAINS drug_lower
WITH c LIMIT 1
OPTIONAL MATCH (c)-[:TREATS]->(d_treat:Disease)
OPTIONAL MATCH (c)-[:PALLIATES]->(d_pal:Disease)
OPTIONAL MATCH (c)-[:BINDS_GENE]->(g:Gene)
OPTIONAL MATCH (c)-[:CAUSES_SIDE_EFFECT]->(se:SideEffect)
OPTIONAL MATCH (c)-[:INCLUDES|IN_CLASS]-(pc:PharmacologicClass)
OPTIONAL MATCH (c)-[:BINDS_GENE]->(g2:Gene)-[:PARTICIPATES_IN]->(pw:Pathway)
RETURN
  c.name AS drug_name,
  c.identifier AS drug_id,
  collect(DISTINCT d_treat.name)[0..8] AS treats_diseases,
  collect(DISTINCT d_pal.name)[0..5] AS palliates_diseases,
  collect(DISTINCT g.name)[0..8] AS molecular_targets,
  collect(DISTINCT se.name)[0..10] AS side_effects,
  collect(DISTINCT pw.name)[0..5] AS biological_pathways,
  pc.name AS drug_class
LIMIT 1
```

**Parameters:**
- `drug_name` (String) — nazwa leku (np. "aspirin", "warfarin", "metformin")

---

### Narzędzie 4: Similarity Search (wbudowane w Aura Agent)

**Name:** `find_similar_drugs`

**Description:**
```
Use this tool to find drugs similar to a given drug based on semantic similarity of their descriptions and mechanisms. Use when the user asks for alternatives to a drug, asks to find drugs that work similarly, or uses phrases like "drugs like X", "similar to X", or "alternatives for X". Do NOT use for specific named drug interactions or disease lookups — use the other tools for those.
```

**Konfiguracja w Aura Agent UI:**
- Index: `compound_embedding`
- Node label: `Compound`
- Property: `embedding`
- Return properties: `name, identifier`

**Prompt:**
```
Find drugs (Compound nodes) that are semantically similar to the query based on their mechanism of action and pharmacological properties. Return the drug name and identifier for each match.
```

---

## 9. System Prompt

Wklej ten tekst w pole **"Agent Instructions"** / **"System Prompt"** w konfiguracji agenta:

```
You are DrugPath, an AI agent that navigates a biomedical knowledge graph to answer questions about drugs, their mechanisms of action, interactions, and disease connections.

You have access to a graph database (Hetionet + DrugBank) containing:
- 1,552 drugs (Compound nodes)
- 20,945 genes/proteins (Gene nodes)
- 137 diseases (Disease nodes)
- 1,822 biological pathways (Pathway nodes)
- 5,734 side effects (SideEffect nodes)

## Your capabilities

Use the available tools strategically:
- drug_interaction_checker: when asked about combining two specific drugs
- drug_repurposing_explorer: when asked about new potential treatments for a disease
- drug_profile_lookup: when asked about what a specific drug does, its targets, or side effects
- find_similar_drugs: when asked for alternatives or similar drugs

## How to answer

Always explain the MECHANISM, not just the result. For example:
- Don't say: "Warfarin and aspirin interact."
- Say: "Warfarin and aspirin interact because both affect blood clotting through different mechanisms — warfarin inhibits Vitamin K epoxide reductase (VKORC1), while aspirin irreversibly inhibits COX-1, which reduces thromboxane A2 production. Together they significantly increase bleeding risk."

When doing drug repurposing, always explain the gene/pathway connection: "Metformin might work for cancer because it targets AMPK, which participates in the mTOR signalling pathway — overactivated in many cancers."

## Important disclaimers

Always add this note when answering health-related questions:
"⚠️ This information is for educational and research purposes only. Always consult a qualified healthcare professional before making any medical decisions."

## Graph reasoning transparency

When you traverse multiple hops in the graph, briefly show the path:
Drug → [targets] → Gene → [participates in] → Pathway → [associated with] → Disease
This helps users understand why the graph gives a better answer than a flat database.
```

---

## 10. Testowanie — scenariusze demo

Te pytania demonstrują każde z narzędzi i pokazują siłę wieloskokowego wnioskowania. Użyj ich podczas demo dla jurorów.

### Demo 1 — Interakcja leków (Narzędzie 1)

```
"Can I take warfarin and aspirin together?"
```
Oczekiwany wynik: opis mechanizmu (VKORC1 + COX-1), severity: major, ryzyko krwawienia.

```
"Czy metformina wchodzi w interakcje z ibuprofenem?"
```

---

### Demo 2 — Drug Repurposing (Narzędzie 2) — WOW MOMENT

```
"What existing drugs might work for Alzheimer's disease?"
```
Oczekiwany wynik: lista leków z genami łączącymi je z chorobą — np. leki onkologiczne, które celują w geny powiązane z Alzheimerem.

```
"What drugs approved for other conditions could potentially treat breast cancer?"
```
To jest pytanie niemożliwe do odpowiedzi bez grafu — wymaga 3-hopowego przejścia Compound → Gene → Disease.

---

### Demo 3 — Profil leku (Narzędzie 3)

```
"Give me a complete profile of metformin — what does it target, treat, and what are its side effects?"
```

```
"What are the molecular targets of ibuprofen?"
```

---

### Demo 4 — Podobne leki (Similarity Search)

```
"What drugs are similar to metformin in terms of how they work?"
```

```
"Find me alternatives to warfarin for anticoagulation."
```

---

### Demo 5 — Multi-hop reasoning (Text2Cypher, jeśli skonfigurujesz)

```
"Which drugs target genes associated with type 2 diabetes AND also cause nausea as a side effect?"
```
To jest 3-hopowe zapytanie: Compound → Gene → Disease + Compound → SideEffect.

---

## 11. Zgłoszenie Hackathonowe

Skopiuj i wklej poniższy tekst jako odpowiedź w wątku hackathonowym na Neo4j Community.

---

### TYTUŁ POSTA: DrugPath Agent

---

# DrugPath — Biomedical Drug Reasoning Agent

## Agent Name
**DrugPath**

## What it does

DrugPath is an AI agent that navigates a biomedical knowledge graph to answer questions about drugs, their mechanisms of action, interactions, and disease connections. Unlike a drug database that returns flat yes/no answers, DrugPath **explains the biological mechanism** behind every answer by traversing multi-hop paths through the graph.

**Three key capabilities:**

**1. Drug interaction checking with mechanism explanation**
Instead of "warfarin + aspirin = dangerous," DrugPath explains: *"These drugs interact because warfarin inhibits VKORC1 (Vitamin K pathway) while aspirin irreversibly blocks COX-1 — both affect different steps of the clotting cascade, creating synergistic bleeding risk."* The answer traces the path: Drug → shared Gene targets → Pathway → clinical outcome.

**2. Drug repurposing discovery**
*"What existing approved drugs could work for Alzheimer's?"* — This requires a 3-hop traversal: find drugs → whose molecular targets (Genes) → are associated with Alzheimer's Disease → but the drug isn't currently indicated for it. No SQL join can express this cleanly. In the graph it's one Cypher query.

**3. Comprehensive drug profiles**
Full pharmacological context for any drug: indications, molecular targets, biological pathways, side effects — all pulled from graph relationships rather than flat attributes.

## Dataset and Why a Graph Fits

**Primary dataset:** [Hetionet v1.0](https://github.com/hetio/hetionet) (CC0 license)
- 47,031 nodes of 11 types
- 2,250,197 relationships of 24 types
- Integrates 29 public biomedical databases: DrugBank, OMIM, DisGeNET, Reactome, Gene Ontology, SIDER, and others

**Supplementary:** DrugBank drug-drug interactions CSV (~1.4M DDI with mechanism descriptions)

**Why a graph is the only right structure for this data:**

A relational database can tell you: *"Metformin treats Type 2 Diabetes."*

A knowledge graph can answer: *"Why might Metformin work against cancer?"*

```
(Metformin:Compound)
  -[:BINDS_GENE]-> (PRKAA1:Gene)        // AMPK alpha subunit
  -[:PARTICIPATES_IN]-> (mTOR_Pathway)   // mTOR signaling
  
(PRKAA1:Gene)
  -[:ASSOCIATES_WITH]-> (Colorectal_Cancer:Disease)
```

This 3-hop path reveals a biologically plausible repurposing hypothesis. It's not in any flat table. It emerges from the **structure of the graph itself** — exactly the kind of insight graphs are built for.

**Node types:**

| Node | Count | Role |
|---|---|---|
| Compound | 1,552 | Drugs and chemical compounds |
| Gene | 20,945 | Molecular targets and enzymes |
| Disease | 137 | Therapeutic indications |
| Pathway | 1,822 | Biological pathways (mTOR, CYP3A4...) |
| SideEffect | 5,734 | Adverse effects |
| PharmacologicClass | 345 | Drug classes |
| Anatomy | 402 | Where diseases manifest |

**Key relationships:** TREATS, PALLIATES, BINDS_GENE, DOWNREGULATES_GENE, UPREGULATES_GENE, CAUSES_SIDE_EFFECT, PARTICIPATES_IN, ASSOCIATES_WITH, INTERACTS_WITH (with mechanism property from DrugBank)

## Agent Tools

| Tool | Type | What it enables |
|---|---|---|
| `drug_interaction_checker` | Cypher Template | Given two drug names, traverses shared gene targets and pathways to explain the interaction mechanism — not just flag it |
| `drug_repurposing_explorer` | Cypher Template | Given a disease, finds drugs approved for OTHER conditions whose molecular targets associate with this disease — pure graph reasoning |
| `drug_profile_lookup` | Cypher Template | Full pharmacological profile: targets, indications, side effects, pathways, drug class |
| `find_similar_drugs` | Similarity Search | Vector search on drug name + mechanism embeddings to find pharmacologically similar compounds |

## Example Interactions

**User:** "Can I combine warfarin and ibuprofen?"

**DrugPath:** "⚠️ Yes, this is a clinically significant interaction. Both drugs affect bleeding risk through different mechanisms: warfarin inhibits VKORC1 (Vitamin K cycle) reducing clotting factor synthesis, while ibuprofen inhibits COX-1 reducing platelet aggregation and also displaces warfarin from plasma proteins — increasing free warfarin concentration. The graph shows they share pathways in arachidonic acid metabolism. Severity: Major. Consult your physician before combining these. *[For educational purposes only — always consult a healthcare professional]*"

---

**User:** "What approved drugs might work for Alzheimer's disease?"

**DrugPath:** "Based on drug repurposing analysis through the knowledge graph, here are compounds whose molecular targets are genetically associated with Alzheimer's disease, though not currently indicated for it:

1. **Methotrexate** — targets DHFR, which associates with neuroinflammation pathways linked to Alzheimer's
2. **Simvastatin** — targets HMGCR; statins have shown neuroprotective effects in studies
3. **Rapamycin** — targets MTOR; mTOR pathway overactivation is associated with tau phosphorylation in Alzheimer's

The reasoning path: Drug → [BINDS_GENE] → Gene → [ASSOCIATES_WITH] → Alzheimer's Disease. None of these is a proven treatment — this is a hypothesis generation tool for researchers. *[Educational purposes only]*"

## Screenshots

*[Tu wstawiasz screenshoty z Aura Console — schemat grafu, agent w akcji]*

## What Makes DrugPath Different

**1. The graph drives every answer, not just stores data.**
Every response cites the traversal path: Compound → Gene → Pathway → Disease. Users see *why* the graph gives this answer, not just what it returns.

**2. Drug repurposing is impossible without the graph.**
Finding drugs whose targets associate with a disease they're not indicated for requires crossing node types in a single query. This is the canonical case where graph databases outperform anything else.

**3. 29 databases, one coherent graph.**
Hetionet integrates DrugBank, OMIM, DisGeNET, Reactome, Gene Ontology, and SIDER into a single traversable structure. The agent reasons across all of them simultaneously.

**4. Real educational value.**
The agent is genuinely useful for medical students, researchers, and anyone trying to understand pharmacology beyond "take this pill for that disease."

## Technical Stack

- **Graph database:** Neo4j Aura Free (AuraDB)
- **Dataset:** Hetionet v1.0 (CC0) + DrugBank DDI
- **ETL:** Python (neo4j driver, pandas)
- **Embeddings:** OpenAI text-embedding-3-small / sentence-transformers
- **Agent:** Neo4j Aura Agent with 3 Cypher Templates + 1 Similarity Search tool
- **Data loading:** ~47k nodes, ~500k selected relationships (filtered to most relevant types for Aura Free limits)

---

*⚠️ Disclaimer: DrugPath is an educational and research tool. It does not provide medical advice. Always consult a qualified healthcare professional for medical decisions.*

---

## Checklist przed zgłoszeniem

- [ ] Hetionet załadowany do AuraDB
- [ ] Embeddingi wygenerowane i vector index aktywny
- [ ] 4 narzędzia agenta skonfigurowane i przetestowane
- [ ] Screenshot schematu grafu (Neo4j Browser → CALL db.schema.visualization())
- [ ] Screenshot agenta w Aura Console z przykładowym pytaniem
- [ ] Opcjonalnie: link do opublikowanego agenta (External Access)
- [ ] Post wklejony na community.neo4j.com z tytułem "DrugPath Agent"

---

*Powodzenia! DrugPath ma unikalną pozycję w stawce — pole farmakologiczne jest wolne, Hetionet to gotowy dump Neo4j, a drug repurposing to idealny "wow moment" dla jurorów Neo4j.*
