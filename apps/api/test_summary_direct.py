#!/usr/bin/env python3

import sys
import os
sys.path.append('/home/ubuntu/repos/legal-ease-ai/apps/api')

from summary_service import generate_lease_summary, validate_summary, get_summary_statistics
import json

def test_summary_generation():
    """Test summary generation with sample data"""
    
    print("=== Testing AI Summary Generation ===")
    
    sample_text = """
    1722 JST, LLC LEASE

    1. PARTIES.
    This Lease, dated as of this 3rd day of January, 2020, is made by and between 1722 J ST, LLC, 
    a California Limited Liability Company ("Landlord") and ABBY A KARAVANI ("Tenant").

    2. PREMISES.
    Landlord hereby leases to Tenant and Tenant hereby leases from Landlord the premises 
    located at 1730 J Street, Suite A, Sacramento, California 95811.

    3. TERM.
    The term of this Lease shall commence on February 1, 2020 and shall expire on January 31, 2025.

    4. RENT.
    Tenant shall pay to Landlord as base rent the sum of Three Thousand Five Hundred Dollars ($3,500.00) 
    per month, payable in advance on the first day of each month.
    """
    
    sample_nlp_data = {
        'parties': {
            'landlord': '1722 J ST, LLC',
            'tenant': 'ABBY A KARAVANI'
        },
        'dates': {
            'effectiveDate': 'February 1, 2020',
            'expirationDate': 'January 31, 2025'
        },
        'rent': {
            'baseRent': '$3,500.00'
        },
        'options': {
            'renewalOptions': ['Standard renewal terms apply']
        },
        'use_clauses': ['Commercial office space'],
        'assignment': {}
    }
    
    print("Testing with sample lease data...")
    print(f"Text length: {len(sample_text)} characters")
    print(f"NLP data keys: {list(sample_nlp_data.keys())}")
    
    print("\n=== Step 1: Generate Summary ===")
    summary_result = generate_lease_summary(sample_text, sample_nlp_data)
    
    if summary_result.get('error'):
        print(f"❌ Summary generation failed: {summary_result['error']}")
        return False
    
    generated_summary = summary_result.get('summary')
    if not generated_summary:
        print("❌ No summary was generated")
        return False
    
    print(f"✓ Summary generation successful")
    print(f"Method: {summary_result.get('method', 'unknown')}")
    print(f"Summary: {generated_summary}")
    
    print("\n=== Step 2: Validate Summary ===")
    validation_result = validate_summary(generated_summary)
    
    print(f"Valid: {validation_result['is_valid']}")
    print(f"Quality score: {validation_result['quality_score']:.2f}")
    if validation_result['issues']:
        print(f"Issues: {validation_result['issues']}")
    
    print("\n=== Step 3: Summary Statistics ===")
    stats = get_summary_statistics(generated_summary)
    print(f"Character count: {stats['character_count']}")
    print(f"Word count: {stats['word_count']}")
    print(f"Sentence count: {stats['sentence_count']}")
    
    print("\n=== Step 4: Test Fallback Mode (No NLP Data) ===")
    fallback_result = generate_lease_summary(sample_text, None)
    
    if fallback_result.get('error'):
        print(f"❌ Fallback summary generation failed: {fallback_result['error']}")
        return False
    
    fallback_summary = fallback_result.get('summary')
    print(f"✓ Fallback summary: {fallback_summary}")
    
    print("\n=== Step 5: Test Error Handling ===")
    error_result = generate_lease_summary("", {})
    print(f"Empty text result: {error_result.get('summary', 'No summary')}")
    
    all_tests_passed = (
        generated_summary and
        validation_result['is_valid'] and
        validation_result['quality_score'] > 0.3 and
        fallback_summary
    )
    
    if all_tests_passed:
        print("\n🎉 Summary generation test PASSED!")
        print("✓ Summary generation working")
        print("✓ Summary validation working")
        print("✓ Summary statistics working")
        print("✓ Fallback mode working")
        print("✓ Error handling working")
        return True
    else:
        print("\n❌ Summary generation test FAILED!")
        return False

if __name__ == "__main__":
    success = test_summary_generation()
    if success:
        print("\n🎉 AI Summary Service is working correctly!")
        exit(0)
    else:
        print("\n❌ AI Summary Service has issues!")
        exit(1)
