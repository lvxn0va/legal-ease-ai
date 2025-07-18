import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from fastapi import HTTPException

logger = logging.getLogger(__name__)

try:
    import pytesseract
    from PIL import Image
    from pdf2image import convert_from_path
    USE_TESSERACT = True
    logger.info("Tesseract OCR libraries found, enabling image-based PDF processing")
except ImportError as e:
    USE_TESSERACT = False
    logger.info(f"Tesseract OCR libraries not found ({e}), image-based PDF processing disabled")

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

try:
    textract_client = boto3.client('textract', region_name=AWS_REGION)
    textract_client.list_adapters()
    USE_TEXTRACT = True
    logger.info("AWS Textract credentials found, using Textract for OCR")
except (NoCredentialsError, ClientError) as e:
    textract_client = None
    USE_TEXTRACT = False
    logger.info(f"AWS credentials not found ({e}), using local OCR libraries")

def extract_text_from_document(file_path: str, mime_type: str) -> Dict[str, Any]:
    """
    Extract text from a document using AWS Textract or local libraries
    
    Returns:
        Dict with 'text', 'pages', 'error' keys
    """
    try:
        if USE_TEXTRACT:
            return _extract_with_textract(file_path, mime_type)
        else:
            return _extract_with_local_libraries(file_path, mime_type)
    except Exception as e:
        logger.error(f"Failed to extract text from {file_path}: {e}")
        return {
            'text': None,
            'pages': [],
            'error': str(e)
        }

def _extract_with_textract(file_path: str, mime_type: str) -> Dict[str, Any]:
    """Extract text using AWS Textract"""
    try:
        with open(file_path, 'rb') as document:
            response = textract_client.detect_document_text(
                Document={'Bytes': document.read()}
            )
        
        text_blocks = []
        pages = []
        current_page = []
        
        for block in response['Blocks']:
            if block['BlockType'] == 'LINE':
                line_text = block['Text']
                text_blocks.append(line_text)
                current_page.append(line_text)
            elif block['BlockType'] == 'PAGE':
                if current_page:
                    pages.append('\n'.join(current_page))
                    current_page = []
        
        if current_page:
            pages.append('\n'.join(current_page))
        
        full_text = '\n'.join(text_blocks)
        
        return {
            'text': full_text,
            'pages': pages,
            'error': None
        }
        
    except Exception as e:
        logger.error(f"Textract extraction failed: {e}")
        raise

def _extract_with_local_libraries(file_path: str, mime_type: str) -> Dict[str, Any]:
    """Extract text using local Python libraries"""
    try:
        if mime_type == 'application/pdf':
            return _extract_from_pdf(file_path)
        elif mime_type in ['application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/msword']:
            return _extract_from_docx(file_path)
        else:
            raise ValueError(f"Unsupported file type: {mime_type}")
            
    except Exception as e:
        logger.error(f"Local extraction failed: {e}")
        raise

def _extract_from_pdf(file_path: str) -> Dict[str, Any]:
    """Extract text from PDF using PyPDF2, with fallback to OCR for image-based PDFs"""
    try:
        import PyPDF2
        
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            pages = []
            text_blocks = []
            
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text.strip():
                        pages.append(page_text)
                        text_blocks.append(page_text)
                except Exception as e:
                    logger.warning(f"Failed to extract text from page {page_num}: {e}")
                    pages.append(f"[Error extracting page {page_num + 1}]")
            
            full_text = '\n\n'.join(text_blocks)
            
            if not full_text.strip() and USE_TESSERACT:
                logger.info("No text extracted with PyPDF2, trying OCR with tesseract")
                return _extract_from_pdf_with_ocr(file_path)
            
            return {
                'text': full_text,
                'pages': pages,
                'error': None
            }
            
    except ImportError:
        return _extract_from_pdf_pdfplumber(file_path)
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        raise

def _extract_from_pdf_pdfplumber(file_path: str) -> Dict[str, Any]:
    """Extract text from PDF using pdfplumber as fallback"""
    try:
        import pdfplumber
        
        pages = []
        text_blocks = []
        
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                try:
                    page_text = page.extract_text()
                    if page_text and page_text.strip():
                        pages.append(page_text)
                        text_blocks.append(page_text)
                except Exception as e:
                    logger.warning(f"Failed to extract text from page {page_num}: {e}")
                    pages.append(f"[Error extracting page {page_num + 1}]")
        
        full_text = '\n\n'.join(text_blocks)
        
        if not full_text.strip() and USE_TESSERACT:
            logger.info("No text extracted with pdfplumber, trying OCR with tesseract")
            return _extract_from_pdf_with_ocr(file_path)
        
        return {
            'text': full_text,
            'pages': pages,
            'error': None
        }
        
    except ImportError:
        if USE_TESSERACT:
            logger.info("pdfplumber not available, trying OCR with tesseract")
            return _extract_from_pdf_with_ocr(file_path)
        else:
            raise ImportError("Neither PyPDF2 nor pdfplumber is available for PDF text extraction")
    except Exception as e:
        logger.error(f"PDF extraction with pdfplumber failed: {e}")
        raise

def _extract_from_docx(file_path: str) -> Dict[str, Any]:
    """Extract text from DOCX using python-docx"""
    try:
        from docx import Document
        
        doc = Document(file_path)
        paragraphs = []
        
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                paragraphs.append(paragraph.text)
        
        full_text = '\n'.join(paragraphs)
        
        pages = [full_text] if full_text.strip() else []
        
        return {
            'text': full_text,
            'pages': pages,
            'error': None
        }
        
    except ImportError:
        raise ImportError("python-docx is not available for DOCX text extraction")
    except Exception as e:
        logger.error(f"DOCX extraction failed: {e}")
        raise

def validate_extracted_text(text: str) -> bool:
    """
    Validate that extracted text meets minimum quality requirements
    """
    if not text or not text.strip():
        logger.warning("Text validation failed: empty or whitespace-only text")
        return False
    
    text_length = len(text.strip())
    if text_length < 50:
        logger.warning(f"Text validation failed: text too short ({text_length} characters, minimum 50)")
        logger.debug(f"Extracted text preview: {repr(text[:200])}")
        return False
    
    alphanumeric_count = sum(1 for c in text if c.isalnum())
    alphanumeric_ratio = alphanumeric_count / len(text) if len(text) > 0 else 0
    if alphanumeric_ratio < 0.3:  # At least 30% alphanumeric
        logger.warning(f"Text validation failed: low alphanumeric ratio ({alphanumeric_ratio:.2%}, minimum 30%)")
        logger.debug(f"Extracted text preview: {repr(text[:200])}")
        return False
    
    logger.info(f"Text validation passed: {text_length} characters, {alphanumeric_ratio:.2%} alphanumeric")
    return True

def _extract_from_pdf_with_ocr(file_path: str) -> Dict[str, Any]:
    """Extract text from PDF using OCR (tesseract) for image-based PDFs"""
    if not USE_TESSERACT:
        raise ImportError("Tesseract OCR libraries not available")
    
    try:
        logger.info(f"Converting PDF to images for OCR: {file_path}")
        images = convert_from_path(file_path)
        
        pages = []
        text_blocks = []
        
        for page_num, image in enumerate(images):
            try:
                logger.info(f"Running OCR on page {page_num + 1}")
                page_text = pytesseract.image_to_string(image, lang='eng')
                
                if page_text.strip():
                    pages.append(page_text)
                    text_blocks.append(page_text)
                    logger.info(f"Extracted {len(page_text)} characters from page {page_num + 1}")
                else:
                    logger.warning(f"No text extracted from page {page_num + 1}")
                    pages.append(f"[No text found on page {page_num + 1}]")
                    
            except Exception as e:
                logger.error(f"OCR failed for page {page_num + 1}: {e}")
                pages.append(f"[OCR error on page {page_num + 1}: {str(e)}]")
        
        full_text = '\n\n'.join(text_blocks)
        
        logger.info(f"OCR completed: extracted {len(full_text)} total characters from {len(images)} pages")
        
        return {
            'text': full_text,
            'pages': pages,
            'error': None
        }
        
    except Exception as e:
        logger.error(f"OCR extraction failed: {e}")
        raise

def get_text_statistics(text: str) -> Dict[str, Any]:
    """
    Get basic statistics about extracted text
    """
    if not text:
        return {
            'character_count': 0,
            'word_count': 0,
            'line_count': 0,
            'paragraph_count': 0
        }
    
    lines = text.split('\n')
    words = text.split()
    paragraphs = [p for p in text.split('\n\n') if p.strip()]
    
    return {
        'character_count': len(text),
        'word_count': len(words),
        'line_count': len(lines),
        'paragraph_count': len(paragraphs)
    }
