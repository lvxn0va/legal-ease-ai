#!/usr/bin/env python3

import os
import sys

sys.path.append("/home/ubuntu/repos/legal-ease-ai/apps/api")

import json

from nlp_service import (extract_lease_terms, get_extraction_statistics,
                         validate_extracted_data)


def test_nlp_with_sample_text():
    sample_lease_text = """
    COMMERCIAL LEASE AGREEMENT
    
    This Lease Agreement ("Lease") is entered into on January 1, 2024, between 
    LANDLORD PROPERTIES LLC, a California limited liability company ("Landlord"), 
    and ABBY A KARAVANI, an individual ("Tenant").
    
    PREMISES: Landlord hereby leases to Tenant the premises located at 
    1730 J Street, Suite A, Sacramento, California 95811 ("Premises").
    
    TERM: The term of this Lease shall commence on February 1, 2024, and shall 
    expire on January 31, 2027, unless sooner terminated in accordance with the 
    terms hereof.
    
    RENT: Tenant shall pay to Landlord base rent in the amount of Three Thousand 
    Five Hundred Dollars ($3,500.00) per month, payable in advance on the first 
    day of each month. Rent shall increase by 3% annually on each anniversary 
    of the commencement date.
    
    RENEWAL OPTION: Tenant shall have the option to renew this Lease for one 
    additional term of three (3) years, provided Tenant is not in default and 
    gives written notice at least ninety (90) days prior to expiration.
    
    PERMITTED USE: The Premises shall be used solely for general office purposes 
    and for no other purpose without the prior written consent of Landlord.
    
    ASSIGNMENT: Tenant may not assign this Lease or sublet the Premises without 
    the prior written consent of Landlord, which consent may be withheld in 
    Landlord's sole discretion.
    
    TERMINATION: Either party may terminate this Lease upon sixty (60) days 
    written notice in the event of material breach by the other party.
    """

    print("=== Testing NLP Extraction with Sample Lease Text ===")
    print(f"Sample text length: {len(sample_lease_text)} characters")
    print(f"Sample text word count: {len(sample_lease_text.split())} words")

    print("\n=== Running NLP Extraction ===")
    nlp_result = extract_lease_terms(sample_lease_text)

    if nlp_result.get("error"):
        print(f"NLP extraction failed: {nlp_result['error']}")
        return False

    print("NLP extraction completed successfully!")
    print(f"Extracted data keys: {list(nlp_result.keys())}")

    print("\n=== Extracted Data ===")
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

    print(f"\n=== Verification of Expected Extractions ===")
    expected_extractions = {
        "parties": ["LANDLORD PROPERTIES LLC", "ABBY A KARAVANI"],
        "dates": ["January 1, 2024", "February 1, 2024", "January 31, 2027"],
        "rent": ["$3,500.00", "3%"],
        "renewal_options": ["three (3) years", "ninety (90) days"],
        "use_clauses": ["general office purposes"],
        "assignment_clauses": ["prior written consent"],
    }

    success_count = 0
    total_checks = len(expected_extractions)

    for field, expected_items in expected_extractions.items():
        field_data = nlp_result.get(field, {})
        found_items = []

        if isinstance(field_data, dict):
            found_items = list(field_data.values())
        elif isinstance(field_data, list):
            found_items = field_data
        elif field_data:
            found_items = [field_data]

        found_any = False
        for expected in expected_items:
            for found in found_items:
                if expected.lower() in str(found).lower():
                    found_any = True
                    break
            if found_any:
                break

        if found_any:
            success_count += 1
            print(f"✓ {field}: Found expected content")
        else:
            print(f"✗ {field}: Expected content not found")
            print(f"  Expected: {expected_items}")
            print(f"  Found: {found_items}")

    print(
        f"\nExtraction Success Rate: {success_count}/{total_checks} ({success_count/total_checks:.1%})"
    )

    return success_count >= total_checks * 0.6  # 60% success rate threshold


if __name__ == "__main__":
    success = test_nlp_with_sample_text()
    if success:
        print("\n🎉 NLP extraction test PASSED!")
        exit(0)
    else:
        print("\n❌ NLP extraction test FAILED!")
        exit(1)
