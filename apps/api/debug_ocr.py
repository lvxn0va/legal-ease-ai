#!/usr/bin/env python3

import sys
import os
sys.path.append('/home/ubuntu/repos/legal-ease-ai/apps/api')

from ocr_service import extract_text_from_document, validate_extracted_text, get_text_statistics, _extract_from_pdf, _extract_from_pdf_pdfplumber

def test_pypdf2_directly():
    file_path = "/home/ubuntu/repos/legal-ease-ai/apps/api/uploads/test-lease-debug.pdf"
    print("=== Testing PyPDF2 directly ===")
    try:
        result = _extract_from_pdf(file_path)
        print(f"PyPDF2 result: {len(result['text']) if result['text'] else 0} characters")
        if result['text']:
            print(f"First 200 chars: {repr(result['text'][:200])}")
        print(f"Pages extracted: {len(result['pages'])}")
        for i, page in enumerate(result['pages'][:2]):
            print(f"Page {i+1} length: {len(page)}")
            if page.strip():
                print(f"Page {i+1} preview: {repr(page[:100])}")
    except Exception as e:
        print(f"PyPDF2 failed: {e}")

def test_pdfplumber_directly():
    file_path = "/home/ubuntu/repos/legal-ease-ai/apps/api/uploads/test-lease-debug.pdf"
    print("\n=== Testing pdfplumber directly ===")
    try:
        result = _extract_from_pdf_pdfplumber(file_path)
        print(f"pdfplumber result: {len(result['text']) if result['text'] else 0} characters")
        if result['text']:
            print(f"First 200 chars: {repr(result['text'][:200])}")
        print(f"Pages extracted: {len(result['pages'])}")
        for i, page in enumerate(result['pages'][:2]):
            print(f"Page {i+1} length: {len(page)}")
            if page.strip():
                print(f"Page {i+1} preview: {repr(page[:100])}")
    except Exception as e:
        print(f"pdfplumber failed: {e}")

def test_ocr():
    file_path = "/home/ubuntu/repos/legal-ease-ai/apps/api/uploads/test-lease-debug.pdf"
    mime_type = "application/pdf"
    
    print(f"Testing OCR on: {file_path}")
    print(f"File exists: {os.path.exists(file_path)}")
    print(f"File size: {os.path.getsize(file_path)} bytes")
    
    if not os.path.exists(file_path):
        print("File not found!")
        return
    
    test_pypdf2_directly()
    test_pdfplumber_directly()
    
    print("\n=== Testing main extraction function ===")
    result = extract_text_from_document(file_path, mime_type)
    
    print(f"Extraction result keys: {result.keys()}")
    print(f"Error: {result.get('error')}")
    
    if result['text']:
        text_length = len(result['text'])
        print(f"Extracted text length: {text_length}")
        print(f"First 200 characters: {repr(result['text'][:200])}")
        
        stats = get_text_statistics(result['text'])
        print(f"Text statistics: {stats}")
        
        is_valid = validate_extracted_text(result['text'])
        print(f"Text validation result: {is_valid}")
    else:
        print("No text extracted from main function")

if __name__ == "__main__":
    test_ocr()
