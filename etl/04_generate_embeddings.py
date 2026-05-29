"""Embed every Compound and build the vector index for similarity search.

Uses OpenAI text-embedding-3-small (1536 dims). Aura Agent's similarity tool
generates query embeddings with the same managed model, so the stored vectors
must match it. Needs OPENAI_API_KEY in .env.

    python etl/04_generate_embeddings.py
"""

import os

from openai import OpenAI
from tqdm import tqdm

from common import get_driver

MODEL = "text-embedding-3-small"
DIMENSIONS = 1536
INDEX_NAME = "compound_embedding"


def embed(client, names):
    resp = client.embeddings.create(model=MODEL, input=[f"Drug: {n}" for n in names])
    return [item.embedding for item in resp.data]


def main():
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is not set (see .env).")

    client = OpenAI()
    driver = get_driver()

    with driver.session() as session:
        compounds = [
            (r["id"], r["name"])
            for r in session.run(
                "MATCH (c:Compound) WHERE c.name IS NOT NULL "
                "RETURN c.identifier AS id, c.name AS name"
            )
        ]
        print(f"Embedding {len(compounds):,} compounds with {MODEL} ...")

        for i in tqdm(range(0, len(compounds), 100), unit="batch"):
            batch = compounds[i:i + 100]
            vectors = embed(client, [name for _, name in batch])
            session.run(
                """
                UNWIND $rows AS row
                MATCH (c:Compound {identifier: row.id})
                CALL db.create.setNodeVectorProperty(c, 'embedding', row.vec)
                """,
                rows=[{"id": cid, "vec": v} for (cid, _), v in zip(batch, vectors)],
            )

        # Recreate so the index dimension always matches the current model.
        session.run(f"DROP INDEX {INDEX_NAME} IF EXISTS")
        session.run(
            f"""
            CREATE VECTOR INDEX {INDEX_NAME}
            FOR (c:Compound) ON (c.embedding)
            OPTIONS {{indexConfig: {{
              `vector.dimensions`: {DIMENSIONS},
              `vector.similarity_function`: 'cosine'
            }}}}
            """
        )

    driver.close()
    print(f"Done. Vector index '{INDEX_NAME}' ready ({DIMENSIONS} dims).")


if __name__ == "__main__":
    main()
