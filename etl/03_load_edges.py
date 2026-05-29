"""Load the filtered Hetionet relationships into Neo4j.

    python etl/03_load_edges.py
"""

from pathlib import Path

import pandas as pd
from tqdm import tqdm

from common import BATCH_SIZE, get_driver

EDGES_FILE = Path("data") / "edges_filtered.tsv"

# metaedge -> (source label, relationship type, target label)
METAEDGE_MAP = {
    "CbG":  ("Compound", "BINDS_GENE", "Gene"),
    "CdG":  ("Compound", "DOWNREGULATES_GENE", "Gene"),
    "CuG":  ("Compound", "UPREGULATES_GENE", "Gene"),
    "CtD":  ("Compound", "TREATS", "Disease"),
    "CpD":  ("Compound", "PALLIATES", "Disease"),
    "CcSE": ("Compound", "CAUSES_SIDE_EFFECT", "SideEffect"),
    "GpPW": ("Gene", "PARTICIPATES_IN", "Pathway"),
    # DaG is stored Disease->Gene in Hetionet; we store it Gene->Disease so the
    # repurposing query reads naturally (gene associated with a disease).
    "DaG":  ("Gene", "ASSOCIATES_WITH", "Disease"),
    "DlA":  ("Disease", "LOCALIZES_TO", "Anatomy"),
    "PCiC": ("PharmacologicClass", "INCLUDES", "Compound"),
}
REVERSED = {"DaG"}  # metaedges whose source/target columns we flip


def load_metaedge(session, metaedge, subset):
    src_label, rel_type, tgt_label = METAEDGE_MAP[metaedge]
    if metaedge in REVERSED:
        subset = subset.rename(columns={"source": "target", "target": "source"})
    records = subset[["source", "target"]].to_dict("records")

    query = f"""
    UNWIND $edges AS edge
    MATCH (s:{src_label} {{identifier: edge.source}})
    MATCH (t:{tgt_label} {{identifier: edge.target}})
    MERGE (s)-[:{rel_type}]->(t)
    """
    desc = f"{src_label}-[{rel_type}]->{tgt_label}"
    for i in tqdm(range(0, len(records), BATCH_SIZE), desc=desc, unit="batch"):
        session.run(query, edges=records[i:i + BATCH_SIZE])
    return len(records)


def main():
    edges = pd.read_csv(EDGES_FILE, sep="\t")

    driver = get_driver()
    total = 0
    with driver.session() as session:
        for metaedge in METAEDGE_MAP:
            subset = edges[edges["metaedge"] == metaedge]
            if not subset.empty:
                total += load_metaedge(session, metaedge, subset)
    driver.close()
    print(f"Loaded {total:,} relationships.")


if __name__ == "__main__":
    main()
