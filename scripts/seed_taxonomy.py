"""
seed_taxonomy.py — seed the `fee_taxonomy` table from the v1 FTC taxonomy.

Inserts/updates each fee type with its FTC clause, description, and a 384-dim
embedding (if sentence-transformers is available) into Eman's pgvector column.
Idempotent: re-running updates existing rows by fee_type. Swap in Matas's
taxonomy later by editing app/agents/ftc_taxonomy.py and re-running this.

    docker compose exec api python scripts/seed_taxonomy.py
    # or locally with DATABASE_URL pointing at Postgres:
    python scripts/seed_taxonomy.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select                          # noqa: E402

from app.agents import embeddings                       # noqa: E402
from app.agents.ftc_taxonomy import all_entries         # noqa: E402
from app.core.database import AsyncSessionLocal         # noqa: E402
from app.models.fee_taxonomy import FeeTaxonomy         # noqa: E402


async def seed() -> None:
    entries = all_entries()
    vecs = embeddings.embed([e.text() for e in entries]) if embeddings.available() else None
    if vecs is None:
        print("⚠ sentence-transformers not available — seeding without embeddings "
              "(install it + re-run to enable pgvector similarity).")

    inserted = updated = 0
    async with AsyncSessionLocal() as session:
        for i, e in enumerate(entries):
            existing = (await session.execute(
                select(FeeTaxonomy).where(FeeTaxonomy.fee_type == e.fee_type)
            )).scalar_one_or_none()
            embedding = vecs[i] if vecs else None
            if existing:
                existing.ftc_clause = e.ftc_clause
                existing.description = e.description
                if embedding is not None:
                    existing.embedding = embedding
                updated += 1
            else:
                session.add(FeeTaxonomy(
                    fee_type=e.fee_type, ftc_clause=e.ftc_clause,
                    description=e.description, embedding=embedding,
                ))
                inserted += 1
        await session.commit()

    print(f"✅ Seeded fee_taxonomy: {inserted} inserted, {updated} updated "
          f"({'with' if vecs else 'without'} embeddings).")


if __name__ == "__main__":
    asyncio.run(seed())
