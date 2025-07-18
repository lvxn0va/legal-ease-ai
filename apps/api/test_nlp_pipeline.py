#!/usr/bin/env python3

import os
import sys

sys.path.append("/home/ubuntu/repos/legal-ease-ai/apps/api")

import json

from models import Document, get_db
from nlp_service import (extract_lease_terms, get_extraction_statistics,
                         validate_extracted_data)


def test_nlp_pipeline():
    db = next(get_db())
    try:
        document = (
            db.query(Document)
            .filter(Document.status == "completed", Document.extracted_text.isnot(None))
            .order_by(Document.updated_at.desc())
            .first()
        )

        if not document:
            print("No completed documents with extracted text found")
            return

        print(f"Testing NLP extraction on document: {document.filename}")
        print(f"Text length: {len(document.extracted_text)} characters")

        print("\n=== Running NLP Extraction ===")
        nlp_result = extract_lease_terms(document.extracted_text)

        if nlp_result.get("error"):
            print(f"NLP extraction failed: {nlp_result['error']}")
            return

        print("NLP extraction completed successfully!")
        print(f"Extracted data keys: {list(nlp_result.keys())}")

        for key, value in nlp_result.items():
            if key != "error" and value:
                print(f"\n{key.upper()}:")
                if isinstance(value, dict):
                    for subkey, subvalue in value.items():
                        print(f"  {subkey}: {subvalue}")
                elif isinstance(value, list):
                    for i, item in enumerate(value[:3]):  # Show first 3 items
                        print(f"  {i+1}: {item}")
                else:
                    print(f"  {value}")

        print("\n=== Validation Results ===")
        validation = validate_extracted_data(nlp_result)
        print(f"Valid: {validation['is_valid']}")
        print(f"Confidence: {validation['confidence_score']:.2%}")
        print(f"Missing fields: {validation['missing_fields']}")
        if validation["warnings"]:
            print(f"Warnings: {validation['warnings']}")

        print("\n=== Extraction Statistics ===")
        stats = get_extraction_statistics(nlp_result)
        print(f"Populated fields: {stats['populated_fields']}/{stats['total_fields']}")

        for field, details in stats["field_details"].items():
            if details["populated"]:
                if "subfields_found" in details:
                    print(
                        f"  {field}: {details['subfields_found']}/{details['total_subfields']} subfields"
                    )
                elif "items_found" in details:
                    print(f"  {field}: {details['items_found']} items")
                else:
                    print(f"  {field}: populated")
            else:
                print(f"  {field}: not found")

        print(f"\n=== JSON Output ===")
        print(json.dumps(nlp_result, indent=2))

    except Exception as e:
        print(f"Error testing NLP pipeline: {e}")
        import traceback

        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    test_nlp_pipeline()
