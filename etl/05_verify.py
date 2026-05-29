"""Sanity-check the loaded graph: counts plus a couple of real queries.

Exits non-zero if the graph is empty, so it can gate the agent setup.

    python etl/05_verify.py
"""

import sys

from common import get_driver


def show(session, title, query, fmt):
    print(f"\n=== {title} ===")
    rows = list(session.run(query))
    if not rows:
        print("  (no results)")
    for r in rows:
        print("  " + fmt(r))
    return rows


def main():
    driver = get_driver()
    with driver.session() as session:
        nodes = show(
            session, "Nodes by label",
            "MATCH (n) RETURN labels(n)[0] AS label, count(*) AS n ORDER BY n DESC",
            lambda r: f"{r['label']:<20} {r['n']:>8,}",
        )
        show(
            session, "Relationships by type",
            "MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS n ORDER BY n DESC",
            lambda r: f"{r['type']:<20} {r['n']:>8,}",
        )
        show(
            session, "What does metformin treat?",
            "MATCH (c:Compound)-[:TREATS]->(d:Disease) "
            "WHERE toLower(c.name) CONTAINS 'metformin' RETURN d.name AS disease",
            lambda r: r["disease"],
        )
        show(
            session, "Repurposing path: metformin -> gene -> cancer",
            "MATCH (c:Compound)-[:BINDS_GENE]->(g:Gene)-[:ASSOCIATES_WITH]->(d:Disease) "
            "WHERE toLower(c.name) CONTAINS 'metformin' AND toLower(d.name) CONTAINS 'cancer' "
            "RETURN g.name AS gene, d.name AS disease LIMIT 5",
            lambda r: f"metformin -> {r['gene']} -> {r['disease']}",
        )
    driver.close()

    if not nodes:
        sys.exit("Graph is empty - run steps 01-03 first.")
    print("\nGraph looks good.")


if __name__ == "__main__":
    main()
