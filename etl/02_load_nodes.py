"""Load Hetionet nodes into Neo4j, one label per node kind.

Creates an identifier index for each label first so the MERGE-by-identifier in
the edge loader stays fast.

    python etl/02_load_nodes.py
"""

from pathlib import Path

import pandas as pd
from tqdm import tqdm

from common import BATCH_SIZE, get_driver

NODES_FILE = Path("data") / "nodes_clean.tsv"

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


def create_indexes(session):
    for label in KIND_TO_LABEL.values():
        session.run(f"CREATE INDEX {label.lower()}_id IF NOT EXISTS FOR (n:{label}) ON (n.identifier)")


def load_label(session, label, records):
    # The label is interpolated (Cypher can't parameterize it); it only ever
    # comes from KIND_TO_LABEL, never user input.
    query = f"""
    UNWIND $nodes AS node
    MERGE (n:{label} {{identifier: node.id}})
    SET n.name = node.name
    """
    for i in tqdm(range(0, len(records), BATCH_SIZE), desc=label, unit="batch"):
        session.run(query, nodes=records[i:i + BATCH_SIZE])


def main():
    nodes = pd.read_csv(NODES_FILE, sep="\t").where(lambda df: df.notnull(), None)

    driver = get_driver()
    with driver.session() as session:
        create_indexes(session)
        for kind, label in KIND_TO_LABEL.items():
            subset = nodes[nodes["kind"] == kind]
            if not subset.empty:
                load_label(session, label, subset[["id", "name"]].to_dict("records"))
    driver.close()
    print("Nodes loaded.")


if __name__ == "__main__":
    main()
