#!/usr/bin/env python3

import os
import sys

sys.path.append("/home/ubuntu/repos/legal-ease-ai/apps/api")

import json

from models import Document, DocumentStatus, create_tables, get_db


def check_database():
    """Check the current state of documents in the database"""

    print("=== Checking Database State ===")

    create_tables()

    db = next(get_db())
    try:
        all_docs = db.query(Document).all()

        print(f"Total documents in database: {len(all_docs)}")

        if not all_docs:
            print("No documents found in database")
            return

        for doc in all_docs:
            print(f"\nDocument ID: {doc.id}")
            print(f"  Filename: {doc.filename}")
            print(f"  Original Filename: {doc.original_filename}")
            print(f"  Status: {doc.status.value}")
            print(f"  File Size: {doc.file_size}")
            print(f"  Created: {doc.created_at}")
            print(f"  Updated: {doc.updated_at}")
            print(f"  Has extracted text: {bool(doc.extracted_text)}")
            print(f"  Has NLP data: {bool(doc.extracted_lease_data)}")
            print(f"  Has AI summary: {bool(doc.ai_summary)}")

            if doc.ocr_extraction_error:
                print(f"  OCR Error: {doc.ocr_extraction_error}")
            if doc.nlp_extraction_error:
                print(f"  NLP Error: {doc.nlp_extraction_error}")

            if doc.ai_summary:
                print(f"  Summary: {doc.ai_summary[:100]}...")

    except Exception as e:
        print(f"Database check failed: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    check_database()
