#!/usr/bin/env python3

import os
import sys

sys.path.append("/home/ubuntu/repos/legal-ease-ai/apps/api")

import json
import shutil
from pathlib import Path

from models import Document, DocumentStatus, create_tables, get_db
from nlp_service import extract_lease_terms
from ocr_service import extract_text_from_document
from summary_service import generate_lease_summary


def test_complete_pipeline():
    """Test the complete OCR -> NLP -> Summary pipeline"""

    print("=== Testing Complete AI Processing Pipeline ===")

    test_file = "/home/ubuntu/repos/legal-ease-ai/samples/lease-documents/1730+J+St+Ste+A+-+Abby+Karavani.pdf"

    if not os.path.exists(test_file):
        print(f"Test file not found: {test_file}")
        return False

    print(f"Testing with file: {os.path.basename(test_file)}")

    print("\n=== Step 1: OCR Text Extraction ===")
    ocr_result = extract_text_from_document(test_file, "application/pdf")

    if ocr_result.get("error"):
        print(f"OCR failed: {ocr_result['error']}")
        return False

    extracted_text = ocr_result["text"]
    print(f"✓ OCR successful: {len(extracted_text)} characters extracted")
    print(f"First 200 chars: {extracted_text[:200]}...")

    print("\n=== Step 2: NLP Key Term Extraction ===")
    nlp_result = extract_lease_terms(extracted_text)

    if nlp_result.get("error"):
        print(f"NLP extraction failed: {nlp_result['error']}")
        return False

    print(f"✓ NLP extraction successful")
    print(f"Extracted data keys: {list(nlp_result.keys())}")

    for key, value in nlp_result.items():
        if key != "error" and value:
            if isinstance(value, dict):
                print(f"  {key}: {len(value)} items")
            elif isinstance(value, list):
                print(f"  {key}: {len(value)} items")
            else:
                print(f"  {key}: {type(value)}")

    print("\n=== Step 3: AI Summary Generation ===")
    summary_result = generate_lease_summary(extracted_text, nlp_result)

    if summary_result.get("error"):
        print(f"Summary generation failed: {summary_result['error']}")
        return False

    generated_summary = summary_result.get("summary")
    if not generated_summary:
        print("No summary was generated")
        return False

    print(f"✓ Summary generation successful")
    print(f"Summary method: {summary_result.get('method', 'unknown')}")
    print(f"Summary length: {len(generated_summary)} characters")
    print(f"Generated summary:")
    print(f"  {generated_summary}")

    print("\n=== Step 4: Pipeline Integration Test ===")

    pipeline_result = {
        "ocr": {
            "success": True,
            "text_length": len(extracted_text),
            "word_count": len(extracted_text.split()),
        },
        "nlp": {
            "success": True,
            "fields_extracted": len(
                [k for k, v in nlp_result.items() if k != "error" and v]
            ),
        },
        "summary": {
            "success": True,
            "summary_length": len(generated_summary),
            "method": summary_result.get("method"),
        },
    }

    print(f"Pipeline Results:")
    print(json.dumps(pipeline_result, indent=2))

    all_successful = (
        pipeline_result["ocr"]["success"]
        and pipeline_result["nlp"]["success"]
        and pipeline_result["summary"]["success"]
    )

    if all_successful:
        print("\n🎉 Complete pipeline test PASSED!")
        print("✓ OCR extraction working")
        print("✓ NLP key term extraction working")
        print("✓ AI summary generation working")
        print("✓ All components integrated successfully")
        return True
    else:
        print("\n❌ Pipeline test FAILED!")
        return False


def test_database_integration():
    """Test that the pipeline works with database storage"""

    print("\n=== Testing Database Integration ===")

    create_tables()

    db = next(get_db())
    try:
        completed_docs = (
            db.query(Document).filter(Document.status == DocumentStatus.COMPLETED).all()
        )

        print(f"Found {len(completed_docs)} completed documents in database")

        if completed_docs:
            doc = completed_docs[0]
            print(f"Sample document: {doc.filename}")
            print(f"  Status: {doc.status.value}")
            print(f"  Has extracted text: {bool(doc.extracted_text)}")
            print(f"  Has NLP data: {bool(doc.extracted_lease_data)}")
            print(f"  Has AI summary: {bool(doc.ai_summary)}")

            if doc.ai_summary:
                print(f"  Summary: {doc.ai_summary[:100]}...")

            return True
        else:
            print("No completed documents found - database integration needs testing")
            return False

    except Exception as e:
        print(f"Database integration test failed: {e}")
        return False
    finally:
        db.close()


if __name__ == "__main__":
    pipeline_success = test_complete_pipeline()

    db_success = test_database_integration()

    if pipeline_success and db_success:
        print("\n🎉 ALL TESTS PASSED!")
        print("The complete AI processing pipeline is working correctly.")
        exit(0)
    else:
        print("\n❌ SOME TESTS FAILED!")
        if not pipeline_success:
            print("- Pipeline processing failed")
        if not db_success:
            print("- Database integration needs work")
        exit(1)
