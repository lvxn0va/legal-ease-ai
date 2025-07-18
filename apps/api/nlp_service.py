import os
import logging
import json
import re
from typing import Dict, Any, Optional, List
from datetime import datetime
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

logger = logging.getLogger(__name__)

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

try:
    comprehend_client = boto3.client('comprehend', region_name=AWS_REGION)
    comprehend_client.list_entities_detection_jobs(MaxResults=1)
    USE_COMPREHEND = True
    logger.info("AWS Comprehend credentials found, using Comprehend for NLP")
except (NoCredentialsError, ClientError) as e:
    comprehend_client = None
    USE_COMPREHEND = False
    logger.info(f"AWS credentials not found ({e}), using local NLP processing")

def extract_lease_terms(text: str) -> Dict[str, Any]:
    """
    Extract key lease terms from document text using AWS Comprehend or local processing
    
    Returns:
        Dict with structured lease data matching ExtractedLeaseData interface
    """
    try:
        if USE_COMPREHEND:
            return _extract_with_comprehend(text)
        else:
            return _extract_with_local_nlp(text)
    except Exception as e:
        logger.error(f"Failed to extract lease terms: {e}")
        return {
            'parties': None,
            'dates': None,
            'rent': None,
            'options': None,
            'use_clauses': None,
            'assignment': None,
            'error': str(e)
        }

def _extract_with_comprehend(text: str) -> Dict[str, Any]:
    """Extract lease terms using AWS Comprehend"""
    try:
        entities_response = comprehend_client.detect_entities(
            Text=text[:5000],  # Comprehend has text length limits
            LanguageCode='en'
        )
        
        key_phrases_response = comprehend_client.detect_key_phrases(
            Text=text[:5000],
            LanguageCode='en'
        )
        
        return _process_comprehend_results(text, entities_response, key_phrases_response)
        
    except Exception as e:
        logger.error(f"Comprehend extraction failed: {e}")
        raise

def _extract_with_local_nlp(text: str) -> Dict[str, Any]:
    """Extract lease terms using local regex and pattern matching"""
    try:
        result = {
            'parties': _extract_parties(text),
            'dates': _extract_dates(text),
            'rent': _extract_rent_info(text),
            'options': _extract_options(text),
            'use_clauses': _extract_use_clauses(text),
            'assignment': _extract_assignment_clauses(text),
            'error': None
        }
        
        logger.info(f"Local NLP extraction completed: found {sum(1 for v in result.values() if v and v != 'error')} data categories")
        return result
        
    except Exception as e:
        logger.error(f"Local NLP extraction failed: {e}")
        raise

def _extract_parties(text: str) -> Optional[Dict[str, str]]:
    """Extract landlord and tenant information"""
    try:
        parties = {}
        
        landlord_patterns = [
            r'(?i)landlord["\s]*:?\s*([^,\n]+(?:LLC|Inc|Corporation|Corp|Company|LP|LLP|Partnership))',
            r'(?i)lessor["\s]*:?\s*([^,\n]+(?:LLC|Inc|Corporation|Corp|Company|LP|LLP|Partnership))',
            r'(?i)between\s+([^,\n]+(?:LLC|Inc|Corporation|Corp|Company|LP|LLP|Partnership))[^,]*(?:landlord|lessor)',
            r'(?i)([^,\n]+(?:LLC|Inc|Corporation|Corp|Company|LP|LLP|Partnership))[^,]*(?:landlord|lessor)'
        ]
        
        tenant_patterns = [
            r'(?i)tenant["\s]*:?\s*([^,\n]+(?:LLC|Inc|Corporation|Corp|Company|LP|LLP|Partnership|DBA)?[^,\n]*)',
            r'(?i)lessee["\s]*:?\s*([^,\n]+(?:LLC|Inc|Corporation|Corp|Company|LP|LLP|Partnership|DBA)?[^,\n]*)',
            r'(?i)and\s+([^,\n]+(?:LLC|Inc|Corporation|Corp|Company|LP|LLP|Partnership|DBA)?[^,\n]*)[^,]*(?:tenant|lessee)',
            r'(?i)([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*(?:DBA|d/b/a)',
            r'(?i)([A-Z][A-Z\s]+[A-Z])\s*(?:DBA|d/b/a)'
        ]
        
        for pattern in landlord_patterns:
            match = re.search(pattern, text)
            if match:
                landlord = match.group(1).strip()
                if len(landlord) > 5 and len(landlord) < 100:  # Reasonable length
                    parties['landlord'] = landlord
                    break
        
        for pattern in tenant_patterns:
            match = re.search(pattern, text)
            if match:
                tenant = match.group(1).strip()
                if len(tenant) > 2 and len(tenant) < 100:  # Reasonable length
                    parties['tenant'] = tenant
                    break
        
        return parties if parties else None
        
    except Exception as e:
        logger.error(f"Failed to extract parties: {e}")
        return None

def _extract_dates(text: str) -> Optional[Dict[str, str]]:
    """Extract lease term dates"""
    try:
        dates = {}
        
        effective_patterns = [
            r'(?i)(?:effective|commencement|start|beginning)\s+date[:\s]*([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
            r'(?i)(?:effective|commence|begin)[s\w]*\s+on\s+([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
            r'(?i)lease\s+(?:term\s+)?(?:shall\s+)?(?:commence|begin)[s\w]*\s+([A-Za-z]+\s+\d{1,2},?\s+\d{4})'
        ]
        
        expiration_patterns = [
            r'(?i)(?:expir|terminat|end)[es\w]*\s+(?:date[:\s]*)?([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
            r'(?i)(?:expir|terminat|end)[es\w]*\s+on\s+([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
            r'(?i)lease\s+(?:term\s+)?(?:shall\s+)?(?:expir|terminat|end)[es\w]*\s+([A-Za-z]+\s+\d{1,2},?\s+\d{4})'
        ]
        
        for pattern in effective_patterns:
            match = re.search(pattern, text)
            if match:
                dates['effectiveDate'] = match.group(1).strip()
                break
        
        for pattern in expiration_patterns:
            match = re.search(pattern, text)
            if match:
                dates['expirationDate'] = match.group(1).strip()
                break
        
        duration_patterns = [
            r'(?i)(?:term|period)\s+of\s+(\d+)\s+(?:year|month)',
            r'(?i)(\d+)[-\s](?:year|month)\s+(?:term|lease)',
            r'(?i)for\s+a\s+(?:term|period)\s+of\s+(\d+)\s+(?:year|month)'
        ]
        
        for pattern in duration_patterns:
            match = re.search(pattern, text)
            if match:
                dates['duration'] = match.group(1).strip()
                break
        
        return dates if dates else None
        
    except Exception as e:
        logger.error(f"Failed to extract dates: {e}")
        return None

def _extract_rent_info(text: str) -> Optional[Dict[str, Any]]:
    """Extract rent schedule and payment information"""
    try:
        rent_info = {}
        
        base_rent_patterns = [
            r'(?i)base\s+rent[:\s]*\$?([\d,]+\.?\d*)\s*(?:per\s+month|monthly|/month)',
            r'(?i)monthly\s+rent[:\s]*\$?([\d,]+\.?\d*)',
            r'(?i)rent[:\s]*\$?([\d,]+\.?\d*)\s*(?:per\s+month|monthly|/month)',
            r'(?i)\$?([\d,]+\.?\d*)\s*(?:per\s+month|monthly|/month)(?:\s+rent)?'
        ]
        
        for pattern in base_rent_patterns:
            match = re.search(pattern, text)
            if match:
                rent_amount = match.group(1).replace(',', '')
                try:
                    amount = float(rent_amount)
                    if 100 <= amount <= 100000:  # Reasonable range
                        rent_info['baseRent'] = f"${rent_amount}"
                        break
                except ValueError:
                    continue
        
        escalation_patterns = [
            r'(?i)(?:escalat|increas)[es\w]*.*?(\d+(?:\.\d+)?%)',
            r'(?i)(?:annual|yearly)\s+(?:escalat|increas)[es\w]*.*?(\d+(?:\.\d+)?%)',
            r'(?i)rent\s+(?:shall\s+)?(?:escalat|increas)[es\w]*.*?(\d+(?:\.\d+)?%)'
        ]
        
        escalation_clauses = []
        for pattern in escalation_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                clause = match.group(0).strip()
                if len(clause) < 200:  # Reasonable length
                    escalation_clauses.append(clause)
        
        if escalation_clauses:
            rent_info['escalationClauses'] = escalation_clauses[:3]  # Limit to 3
        
        return rent_info if rent_info else None
        
    except Exception as e:
        logger.error(f"Failed to extract rent info: {e}")
        return None

def _extract_options(text: str) -> Optional[Dict[str, List[str]]]:
    """Extract renewal and termination options"""
    try:
        options = {}
        
        renewal_patterns = [
            r'(?i)(?:renewal|extend|extension)\s+option[s]?[^.]*\.',
            r'(?i)tenant\s+(?:may|shall have|has)\s+(?:the\s+)?(?:right|option)\s+to\s+(?:renew|extend)[^.]*\.',
            r'(?i)(?:renew|extend)\s+(?:this\s+)?lease[^.]*\.'
        ]
        
        renewal_options = []
        for pattern in renewal_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                option = match.group(0).strip()
                if len(option) < 300:  # Reasonable length
                    renewal_options.append(option)
        
        if renewal_options:
            options['renewalOptions'] = renewal_options[:3]  # Limit to 3
        
        termination_patterns = [
            r'(?i)(?:early\s+)?terminat[ion\w]*[^.]*\.',
            r'(?i)tenant\s+(?:may|shall have|has)\s+(?:the\s+)?(?:right|option)\s+to\s+terminat[e\w]*[^.]*\.',
            r'(?i)(?:break|cancel)[^.]*lease[^.]*\.'
        ]
        
        termination_clauses = []
        for pattern in termination_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                clause = match.group(0).strip()
                if len(clause) < 300:  # Reasonable length
                    termination_clauses.append(clause)
        
        if termination_clauses:
            options['terminationClauses'] = termination_clauses[:3]  # Limit to 3
        
        return options if options else None
        
    except Exception as e:
        logger.error(f"Failed to extract options: {e}")
        return None

def _extract_use_clauses(text: str) -> Optional[List[str]]:
    """Extract permitted and prohibited uses"""
    try:
        use_clauses = []
        
        use_patterns = [
            r'(?i)(?:permitted|allowed)\s+use[s]?[^.]*\.',
            r'(?i)(?:prohibited|forbidden|not\s+permitted)\s+use[s]?[^.]*\.',
            r'(?i)premises\s+(?:shall|may)\s+(?:only\s+)?be\s+used[^.]*\.',
            r'(?i)tenant\s+(?:shall|may)\s+use\s+(?:the\s+)?premises[^.]*\.'
        ]
        
        for pattern in use_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                clause = match.group(0).strip()
                if len(clause) < 300:  # Reasonable length
                    use_clauses.append(clause)
        
        return use_clauses[:5] if use_clauses else None  # Limit to 5
        
    except Exception as e:
        logger.error(f"Failed to extract use clauses: {e}")
        return None

def _extract_assignment_clauses(text: str) -> Optional[List[str]]:
    """Extract assignment and subletting clauses"""
    try:
        assignment_clauses = []
        
        assignment_patterns = [
            r'(?i)(?:assignment|assign)[^.]*\.',
            r'(?i)(?:sublet|subletting|sublease)[^.]*\.',
            r'(?i)tenant\s+(?:may|shall)\s+not\s+(?:assign|sublet)[^.]*\.',
            r'(?i)(?:transfer|convey)[^.]*lease[^.]*\.'
        ]
        
        for pattern in assignment_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                clause = match.group(0).strip()
                if len(clause) < 300:  # Reasonable length
                    assignment_clauses.append(clause)
        
        return assignment_clauses[:3] if assignment_clauses else None  # Limit to 3
        
    except Exception as e:
        logger.error(f"Failed to extract assignment clauses: {e}")
        return None

def _process_comprehend_results(text: str, entities_response: Dict, key_phrases_response: Dict) -> Dict[str, Any]:
    """Process AWS Comprehend results to extract lease-specific terms"""
    try:
        entities = entities_response.get('Entities', [])
        key_phrases = key_phrases_response.get('KeyPhrases', [])
        
        result = _extract_with_local_nlp(text)
        
        persons = [e['Text'] for e in entities if e['Type'] == 'PERSON' and e['Score'] > 0.8]
        organizations = [e['Text'] for e in entities if e['Type'] == 'ORGANIZATION' and e['Score'] > 0.8]
        dates = [e['Text'] for e in entities if e['Type'] == 'DATE' and e['Score'] > 0.8]
        
        if not result.get('parties') and (persons or organizations):
            parties = {}
            if organizations:
                parties['landlord'] = organizations[0]
                if len(organizations) > 1:
                    parties['tenant'] = organizations[1]
                elif persons:
                    parties['tenant'] = persons[0]
            elif persons:
                if len(persons) > 1:
                    parties['landlord'] = persons[0]
                    parties['tenant'] = persons[1]
            
            if parties:
                result['parties'] = parties
        
        if not result.get('dates') and dates:
            date_info = {}
            if len(dates) >= 2:
                date_info['effectiveDate'] = dates[0]
                date_info['expirationDate'] = dates[1]
            elif len(dates) == 1:
                date_info['effectiveDate'] = dates[0]
            
            if date_info:
                result['dates'] = date_info
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to process Comprehend results: {e}")
        return _extract_with_local_nlp(text)

def validate_extracted_data(extracted_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and clean extracted lease data
    """
    try:
        validation_result = {
            'is_valid': False,
            'confidence_score': 0.0,
            'missing_fields': [],
            'warnings': []
        }
        
        required_fields = ['parties', 'dates', 'rent']
        found_fields = 0
        
        for field in required_fields:
            if extracted_data.get(field):
                found_fields += 1
            else:
                validation_result['missing_fields'].append(field)
        
        validation_result['confidence_score'] = found_fields / len(required_fields)
        validation_result['is_valid'] = validation_result['confidence_score'] >= 0.5
        
        if not extracted_data.get('parties'):
            validation_result['warnings'].append("No party information found")
        if not extracted_data.get('dates'):
            validation_result['warnings'].append("No lease term dates found")
        if not extracted_data.get('rent'):
            validation_result['warnings'].append("No rent information found")
        
        logger.info(f"Data validation: {validation_result['confidence_score']:.2%} confidence, "
                   f"{len(validation_result['missing_fields'])} missing fields")
        
        return validation_result
        
    except Exception as e:
        logger.error(f"Failed to validate extracted data: {e}")
        return {
            'is_valid': False,
            'confidence_score': 0.0,
            'missing_fields': required_fields,
            'warnings': [f"Validation error: {str(e)}"]
        }

def get_extraction_statistics(extracted_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get statistics about the extraction results
    """
    try:
        stats = {
            'total_fields': 0,
            'populated_fields': 0,
            'field_details': {}
        }
        
        field_mapping = {
            'parties': ['landlord', 'tenant'],
            'dates': ['effectiveDate', 'expirationDate', 'duration'],
            'rent': ['baseRent', 'escalationClauses'],
            'options': ['renewalOptions', 'terminationClauses'],
            'use_clauses': [],
            'assignment': []
        }
        
        for field, subfields in field_mapping.items():
            field_data = extracted_data.get(field)
            if field_data:
                stats['populated_fields'] += 1
                if isinstance(field_data, dict):
                    populated_subfields = len([k for k in subfields if field_data.get(k)])
                    stats['field_details'][field] = {
                        'populated': True,
                        'subfields_found': populated_subfields,
                        'total_subfields': len(subfields)
                    }
                elif isinstance(field_data, list):
                    stats['field_details'][field] = {
                        'populated': True,
                        'items_found': len(field_data)
                    }
                else:
                    stats['field_details'][field] = {'populated': True}
            else:
                stats['field_details'][field] = {'populated': False}
            
            stats['total_fields'] += 1
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get extraction statistics: {e}")
        return {'error': str(e)}
