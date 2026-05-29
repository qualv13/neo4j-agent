"""Download Hetionet v1.0 and filter it down to the edges DrugPath needs.

Writes data/nodes_clean.tsv (all nodes) and data/edges_filtered.tsv (the subset
of relationships that fit AuraDB Free's 400k limit). Run with --force to
re-download the source files.

    python etl/01_download_hetionet.py
"""

import argparse
import gzip
import urllib.request
from pathlib import Path

import pandas as pd

NODES_URL = "https://github.com/hetio/hetionet/raw/main/hetnet/tsv/hetionet-v1.0-nodes.tsv"
EDGES_URL = "https://github.com/hetio/hetionet/raw/main/hetnet/tsv/hetionet-v1.0-edges.sif.gz"

DATA = Path("data")
RAW_NODES = DATA / "nodes.tsv"
RAW_EDGES = DATA / "edges.sif.gz"
CLEAN_NODES = DATA / "nodes_clean.tsv"
FILTERED_EDGES = DATA / "edges_filtered.tsv"

# The metaedges we keep. All nodes fit under AuraDB Free, but the full 2.25M
# relationships do not, so we load only the ones the agent's tools traverse.
KEEP = {
    "CbG",   # Compound binds Gene
    "CdG",   # Compound downregulates Gene
    "CuG",   # Compound upregulates Gene
    "CtD",   # Compound treats Disease
    "CpD",   # Compound palliates Disease
    "CcSE",  # Compound causes Side Effect
    "GpPW",  # Gene participates in Pathway
    "DaG",   # Disease associates Gene
    "DlA",   # Disease localizes to Anatomy
    "PCiC",  # Pharmacologic Class includes Compound
}


def download(url, dest, force):
    if dest.exists() and not force:
        print(f"  {dest} already present, skipping download")
        return
    print(f"  downloading {dest.name} ...")
    urllib.request.urlretrieve(url, dest)


def main(force):
    DATA.mkdir(exist_ok=True)

    print("Downloading Hetionet ...")
    download(NODES_URL, RAW_NODES, force)
    download(EDGES_URL, RAW_EDGES, force)

    nodes = pd.read_csv(RAW_NODES, sep="\t")  # columns: id, name, kind
    print(f"\n{len(nodes):,} nodes:")
    print(nodes["kind"].value_counts().to_string())

    with gzip.open(RAW_EDGES, "rt", encoding="utf-8") as f:
        edges = pd.read_csv(f, sep="\t")  # columns: source, metaedge, target
    kept = edges[edges["metaedge"].isin(KEEP)]
    print(f"\n{len(kept):,} relationships kept (of {len(edges):,}):")
    print(kept["metaedge"].value_counts().to_string())

    nodes.to_csv(CLEAN_NODES, sep="\t", index=False)
    kept.to_csv(FILTERED_EDGES, sep="\t", index=False)
    print(f"\nWrote {CLEAN_NODES} and {FILTERED_EDGES}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="re-download source files")
    main(parser.parse_args().force)
