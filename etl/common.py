"""Shared helpers for the ETL scripts: config loading and a Neo4j driver."""

import os
import sys

from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

BATCH_SIZE = 1000


def get_driver():
    """Return a Neo4j driver built from the NEO4J_* environment variables."""
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USERNAME")
    password = os.getenv("NEO4J_PASSWORD")

    if not all((uri, user, password)):
        sys.exit(
            "Missing Neo4j credentials. Copy .env.example to .env and set "
            "NEO4J_URI, NEO4J_USERNAME and NEO4J_PASSWORD."
        )

    driver = GraphDatabase.driver(uri, auth=(user, password))
    driver.verify_connectivity()
    return driver
