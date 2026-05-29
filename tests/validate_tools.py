"""Run the agent's Cypher tools against the live database and print the results.

A quick way to confirm the three Cypher templates in agent/tools/ return sensible
data before wiring them into the Aura Agent UI (find_similar_drugs is a built-in
vector tool, configured in the UI, so it isn't covered here).

    python tests/validate_tools.py
"""

import sys
from pathlib import Path

# Reuse the ETL driver/config helper.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "etl"))
from common import get_driver  # noqa: E402

TOOLS_DIR = Path("agent") / "tools"


def read_cypher(name: str) -> str:
    return (TOOLS_DIR / name).read_text(encoding="utf-8")


def run(driver, title, cypher, params):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)
    with driver.session() as session:
        records = list(session.run(cypher, **params))
    if not records:
        print("  (no rows)")
        return
    for rec in records:
        d = dict(rec)
        for k, v in d.items():
            if isinstance(v, list):
                v = ", ".join(str(x) for x in v) if v else "—"
            print(f"  {k}: {v}")
        print("  " + "-" * 40)


def sample_names(driver):
    """Pull real Hetionet names so demo questions use exact terms."""
    print("\n" + "=" * 70)
    print("Sample real names in the graph (use these in demos)")
    print("=" * 70)
    queries = {
        "Diseases containing 'cancer'":
            "MATCH (d:Disease) WHERE toLower(d.name) CONTAINS 'cancer' "
            "RETURN d.name AS n ORDER BY n LIMIT 15",
        "Diseases containing 'alzheimer'":
            "MATCH (d:Disease) WHERE toLower(d.name) CONTAINS 'alzheimer' "
            "RETURN d.name AS n LIMIT 5",
        "A few well-connected drugs":
            "MATCH (c:Compound)-[:BINDS_GENE]->(:Gene) "
            "WITH c, count(*) AS deg ORDER BY deg DESC "
            "RETURN c.name AS n LIMIT 15",
    }
    with driver.session() as session:
        for label, q in queries.items():
            names = [r["n"] for r in session.run(q)]
            print(f"  {label}:")
            print(f"    {', '.join(names) if names else '—'}")


def main() -> int:
    driver = get_driver()
    try:
        driver.verify_connectivity()

        run(
            driver,
            "TOOL 1 — drug_interaction_checker (warfarin + acetylsalicylic acid)",
            read_cypher("drug_interaction_checker.cypher"),
            {"drug1_name": "warfarin", "drug2_name": "acetylsalicylic acid"},
        )
        run(
            driver,
            "TOOL 2 — drug_repurposing_explorer (breast cancer)  [WOW moment]",
            read_cypher("drug_repurposing_explorer.cypher"),
            {"disease_name": "breast cancer"},
        )
        run(
            driver,
            "TOOL 2 — drug_repurposing_explorer (Alzheimer's disease)",
            read_cypher("drug_repurposing_explorer.cypher"),
            {"disease_name": "alzheimer"},
        )
        run(
            driver,
            "TOOL 3 — drug_profile_lookup (metformin)",
            read_cypher("drug_profile_lookup.cypher"),
            {"drug_name": "metformin"},
        )

        sample_names(driver)
    finally:
        driver.close()
    print("\nValidation complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
