import os
import logging
import json
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

logger = logging.getLogger(__name__)

try:
    comprehend_client = boto3.client('comprehend')
    AWS_AVAILABLE = True
    logger.info("AWS Comprehend client initialized successfully")
except (NoCredentialsError, Exception) as e:
    comprehend_client = None
    AWS_AVAILABLE = False
    logger.warning(f"AWS credentials not found ({e}), using local summary generation")

def generate_lease_summary(extracted_text: str, extracted_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Generate a concise summary of a lease document using AI/ML services
    
    Args:
        extracted_text: The full text content of the lease document
        extracted_data: Optional structured data extracted from the lease
        
    Returns:
        Dict containing the generated summary and metadata
    """
    try:
        if AWS_AVAILABLE:
            return _generate_summary_with_comprehend(extracted_text, extracted_data)
        else:
            return _generate_summary_locally(extracted_text, extracted_data)
            
    except Exception as e:
        logger.error(f"Failed to generate summary: {e}")
        return {
            'summary': None,
            'error': f"Summary generation failed: {str(e)}",
            'method': 'error'
        }

def _generate_summary_with_comprehend(extracted_text: str, extracted_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Generate summary using AWS Comprehend
    """
    try:
        
        key_phrases_response = comprehend_client.detect_key_phrases(
            Text=extracted_text[:5000],  # Comprehend has text length limits
            LanguageCode='en'
        )
        
        key_phrases = [phrase['Text'] for phrase in key_phrases_response['KeyPhrases'][:10]]
        
        summary = _create_structured_summary_with_comprehend(extracted_text, extracted_data, key_phrases)
        
        return {
            'summary': summary,
            'key_phrases': key_phrases,
            'method': 'aws_comprehend',
            'error': None
        }
        
    except ClientError as e:
        logger.error(f"AWS Comprehend error: {e}")
        return _generate_summary_locally(extracted_text, extracted_data)
    except Exception as e:
        logger.error(f"Comprehend summary generation failed: {e}")
        return _generate_summary_locally(extracted_text, extracted_data)

def _generate_summary_locally(extracted_text: str, extracted_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Generate summary using local text processing and extracted structured data
    """
    try:
        summary_parts = []
        
        if extracted_data and isinstance(extracted_data, dict):
            parties = extracted_data.get('parties', {})
            if isinstance(parties, dict) and parties.get('landlord') and parties.get('tenant'):
                summary_parts.append(f"This lease agreement is between {parties['landlord']} (Landlord) and {parties['tenant']} (Tenant).")
            
            dates = extracted_data.get('dates', {})
            if isinstance(dates, dict) and dates.get('effectiveDate') and dates.get('expirationDate'):
                summary_parts.append(f"The lease term runs from {dates['effectiveDate']} to {dates['expirationDate']}.")
            
            rent = extracted_data.get('rent', {})
            if isinstance(rent, dict) and rent.get('baseRent'):
                rent_text = f"The base rent is {rent['baseRent']}"
                if rent.get('escalationClauses') and isinstance(rent.get('escalationClauses'), list):
                    escalation = rent['escalationClauses'][0] if rent['escalationClauses'] else ""
                    if escalation:
                        rent_text += f" with {escalation}"
                rent_text += "."
                summary_parts.append(rent_text)
            
            options = extracted_data.get('options', {})
            if isinstance(options, dict) and options.get('renewalOptions'):
                renewal_options = options['renewalOptions']
                if isinstance(renewal_options, list) and renewal_options:
                    renewal_info = renewal_options[0] if renewal_options else ""
                    if renewal_info and len(str(renewal_info)) < 200:  # Keep it concise
                        summary_parts.append(f"Renewal terms: {renewal_info}")
            
            use_clauses = extracted_data.get('use_clauses', [])
            if isinstance(use_clauses, list) and use_clauses:
                use_info = use_clauses[0] if use_clauses else ""
                if use_info and len(str(use_info)) < 150:
                    summary_parts.append(f"Permitted use: {use_info}")
        
        if not summary_parts:
            summary_parts = _extract_summary_from_text(extracted_text)
        
        summary = " ".join(summary_parts)
        
        if len(summary) > 500:
            summary = summary[:497] + "..."
        
        return {
            'summary': summary,
            'method': 'local_extraction',
            'error': None
        }
        
    except Exception as e:
        logger.error(f"Local summary generation failed: {e}")
        return {
            'summary': "Unable to generate summary due to processing error.",
            'method': 'fallback',
            'error': str(e)
        }

def _create_structured_summary_with_comprehend(extracted_text: str, extracted_data: Optional[Dict[str, Any]], key_phrases: list) -> str:
    """
    Create a structured summary using AWS Comprehend insights and extracted data
    """
    summary_parts = []
    
    if extracted_data and isinstance(extracted_data, dict):
        parties = extracted_data.get('parties', {})
        if isinstance(parties, dict) and parties.get('landlord') and parties.get('tenant'):
            summary_parts.append(f"This lease agreement is between {parties['landlord']} (Landlord) and {parties['tenant']} (Tenant).")
        
        dates = extracted_data.get('dates', {})
        if isinstance(dates, dict) and dates.get('effectiveDate') and dates.get('expirationDate'):
            summary_parts.append(f"The lease term runs from {dates['effectiveDate']} to {dates['expirationDate']}.")
        
        rent = extracted_data.get('rent', {})
        if isinstance(rent, dict) and rent.get('baseRent'):
            rent_text = f"The base rent is {rent['baseRent']}"
            if rent.get('escalationClauses') and isinstance(rent.get('escalationClauses'), list):
                escalation = rent['escalationClauses'][0] if rent['escalationClauses'] else ""
                if escalation:
                    rent_text += f" with {escalation}"
            rent_text += "."
            summary_parts.append(rent_text)
    
    # Enhance with key phrases from Comprehend
    if key_phrases and len(summary_parts) < 3:
        relevant_phrases = [phrase for phrase in key_phrases if any(term in phrase.lower() 
                           for term in ['lease', 'rent', 'tenant', 'landlord', 'property', 'agreement'])]
        if relevant_phrases:
            summary_parts.append(f"Key terms include: {', '.join(relevant_phrases[:3])}.")
    
    # Fallback to text analysis if no structured data
    if not summary_parts:
        summary_parts = _extract_summary_from_text(extracted_text)
    
    summary = " ".join(summary_parts)
    return summary[:500] + "..." if len(summary) > 500 else summary

def _extract_summary_from_text(text: str) -> list:
    """
    Extract key information from raw text when structured data is not available
    """
    summary_parts = []
    
    text_lower = text.lower()
    
    if "landlord" in text_lower and "tenant" in text_lower:
        summary_parts.append("This is a lease agreement between a landlord and tenant.")
    
    import re
    
    date_patterns = [
        r'(\w+ \d{1,2}, \d{4})',
        r'(\d{1,2}/\d{1,2}/\d{4})',
        r'(\d{1,2}-\d{1,2}-\d{4})'
    ]
    
    dates_found = []
    for pattern in date_patterns:
        matches = re.findall(pattern, text)
        dates_found.extend(matches[:2])  # Limit to first 2 dates
    
    if len(dates_found) >= 2:
        summary_parts.append(f"The lease term is from {dates_found[0]} to {dates_found[1]}.")
    
    rent_patterns = [
        r'\$[\d,]+\.?\d*',
        r'(\d+) dollars?'
    ]
    
    for pattern in rent_patterns:
        matches = re.findall(pattern, text)
        if matches:
            rent_amount = matches[0]
            summary_parts.append(f"The rent amount is {rent_amount}.")
            break
    
    if not summary_parts:
        summary_parts.append("This document contains lease agreement terms and conditions.")
    
    return summary_parts

def validate_summary(summary: str) -> Dict[str, Any]:
    """
    Validate the generated summary for quality and completeness
    """
    validation_result = {
        'is_valid': True,
        'quality_score': 0.0,
        'issues': []
    }
    
    if not summary or len(summary.strip()) == 0:
        validation_result['is_valid'] = False
        validation_result['issues'].append("Summary is empty")
        return validation_result
    
    if len(summary) < 20:
        validation_result['issues'].append("Summary is too short")
        validation_result['quality_score'] -= 0.3
    
    if len(summary) > 1000:
        validation_result['issues'].append("Summary is too long")
        validation_result['quality_score'] -= 0.2
    
    lease_terms = ['lease', 'rent', 'tenant', 'landlord', 'term', 'agreement']
    terms_found = sum(1 for term in lease_terms if term.lower() in summary.lower())
    
    if terms_found >= 3:
        validation_result['quality_score'] += 0.5
    elif terms_found >= 1:
        validation_result['quality_score'] += 0.2
    else:
        validation_result['issues'].append("Summary lacks key lease terminology")
        validation_result['quality_score'] -= 0.3
    
    sentence_count = len([s for s in summary.split('.') if s.strip()])
    if sentence_count >= 2:
        validation_result['quality_score'] += 0.3
    elif sentence_count == 1:
        validation_result['quality_score'] += 0.1
    else:
        validation_result['issues'].append("Summary lacks proper sentence structure")
        validation_result['quality_score'] -= 0.2
    
    validation_result['quality_score'] = max(0.0, min(1.0, validation_result['quality_score'] + 0.5))
    
    if validation_result['quality_score'] < 0.3:
        validation_result['is_valid'] = False
    
    return validation_result

def get_summary_statistics(summary: str) -> Dict[str, Any]:
    """
    Get statistics about the generated summary
    """
    if not summary:
        return {
            'character_count': 0,
            'word_count': 0,
            'sentence_count': 0
        }
    
    words = summary.split()
    sentences = [s.strip() for s in summary.split('.') if s.strip()]
    
    return {
        'character_count': len(summary),
        'word_count': len(words),
        'sentence_count': len(sentences)
    }
