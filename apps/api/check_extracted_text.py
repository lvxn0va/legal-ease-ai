#!/usr/bin/env python3

import os
import sys

sys.path.append("/home/ubuntu/repos/legal-ease-ai/apps/api")

from models import Document, get_db


def check_extracted_text():
    db = next(get_db())
    try:
        document = (
            db.query(Document)
            .filter(Document.status == "completed")
            .order_by(Document.updated_at.desc())
            .first()
        )

        if not document:
            print("No completed documents found")
            return

        print(f"Document ID: {document.id}")
        print(f"Filename: {document.filename}")
        print(f"Status: {document.status.value}")
        print(f"Updated: {document.updated_at}")

        if document.extracted_text:
            text_length = len(document.extracted_text)
            print(f"Extracted text length: {text_length} characters")
            print(f"First 200 characters: {repr(document.extracted_text[:200])}")

            words = len(document.extracted_text.split())
            lines = len(document.extracted_text.split("\n"))
            print(f"Word count: {words}")
            print(f"Line count: {lines}")
        else:
            print("No extracted text found")

        if document.extraction_error:
            print(f"Extraction error: {document.extraction_error}")
        else:
            print("No extraction errors")

    except Exception as e:
        print(f"Error checking database: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    check_extracted_text()
