#!/usr/bin/env python3

from models import create_tables, engine
from sqlalchemy import text


def update_database():
    """Update database schema to include new tables"""
    print("Updating database schema...")

    create_tables()

    with engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='document_feedback';"
            )
        )
        if result.fetchone():
            print("✓ DocumentFeedback table exists")
        else:
            print("✗ DocumentFeedback table not found")

    print("Database update complete!")


if __name__ == "__main__":
    update_database()
