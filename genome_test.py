"""
Quick end-to-end test: run genome on the fixture listings and print match results.
Expects orbit mock data already in DB (run orbit's pull first, or use ORBIT_RUN_INITIAL_PULL=true).

Usage:
    python genome_test.py
"""
import os
import sys

os.environ.setdefault("DATABASE_URL", "postgresql://nml:nml_dev_password@localhost:5432/nml_shelf")

from shared.db import SessionLocal
from orbit.jobs import pull_salla_job, pull_meta_ads_job
from genome.embedder import get_embedder
from genome.matcher import run_genome_pass


def main():
    db = SessionLocal()

    # Ensure listings are present; pull if not
    from sqlalchemy import text
    count = db.execute(text("SELECT COUNT(*) FROM listings")).scalar()
    if count == 0:
        print("No listings found — running orbit mock pull first...")
        pull_salla_job()
        pull_meta_ads_job()
        count = db.execute(text("SELECT COUNT(*) FROM listings")).scalar()
    print(f"Listings in DB: {count}")

    # Clear any prior genome results so the pass runs on everything (FK order)
    db.execute(text("UPDATE listings SET product_id = NULL, resolved_by = NULL"))
    db.execute(text("DELETE FROM recommendations"))
    db.execute(text("DELETE FROM products"))
    db.commit()
    print("Cleared prior genome results.\n")

    embedder = get_embedder()
    result = run_genome_pass(db, embedder)
    db.close()

    print(f"\n=== Genome pass results ===")
    print(f"  Total listings processed : {result.total_unresolved}")
    print(f"  New canonical products   : {result.created}")
    print(f"  Cross-store matches      : {result.matched}")
    print(f"  Queued for review        : {result.queued_for_review}")

    if result.match_details:
        print(f"\n=== Cross-store matches (the interesting ones) ===")
        for m in result.match_details:
            if m["resolved_by"] == "genome:text_embedding":
                print(
                    f"  MATCH  '{m['listing_title']}' ({m['store_name']})\n"
                    f"    → canonical '{m['canonical_name_ar']}'\n"
                    f"    → product_id {m['matched_product_id']}\n"
                    f"    → similarity {m['similarity']}\n"
                )
    else:
        print("\nNo cross-store matches found.")


if __name__ == "__main__":
    main()
