import tempfile
import docx2txt
import PyPDF2
import os
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

def extract_text_from_file(filepath):
    """
    Extract text from uploaded file based on extension
    """
    try:
        extension = filepath.split('.')[-1].lower()
        if extension == 'pdf':
            return extract_text_from_pdf(filepath)
        elif extension == 'docx':
            return extract_text_from_docx(filepath)
        elif extension == 'doc':
            # For .doc files, try to use python-docx first
            try:
                return extract_text_from_docx(filepath)
            except Exception:
                logger.warning(f"Failed to extract text from .doc file: {filepath}")
                return ""
        else:
            logger.warning(f"Unsupported file extension: {extension}")
            return ""
    except Exception as e:
        logger.error(f"Error extracting text from file {filepath}: {str(e)}")
        return ""

def extract_text_from_pdf(filepath):
    """
    Extract text from PDF file
    """
    text = ""
    try:
        with open(filepath, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text.strip()
    except Exception as e:
        logger.error(f"Error extracting text from PDF {filepath}: {str(e)}")
        return ""

def extract_text_from_docx(filepath):
    """
    Extract text from DOCX file
    """
    try:
        text = docx2txt.process(filepath)
        return text.strip() if text else ""
    except Exception as e:
        logger.error(f"Error extracting text from DOCX {filepath}: {str(e)}")
        return ""

def validate_file(file):
    """
    Validate uploaded file
    """
    errors = []
    
    # Check file size
    max_size = getattr(settings, 'RESUME_PROCESSING', {}).get('MAX_FILE_SIZE', 10 * 1024 * 1024)
    if file.size > max_size:
        errors.append(f"File size must be less than {max_size // (1024*1024)}MB")
    
    # Check file extension
    allowed_extensions = getattr(settings, 'RESUME_PROCESSING', {}).get('ALLOWED_EXTENSIONS', ['.pdf', '.doc', '.docx'])
    file_extension = '.' + file.name.split('.')[-1].lower()
    if file_extension not in allowed_extensions:
        errors.append(f"Only {', '.join(allowed_extensions)} files are allowed")
    
    return errors

def format_file_size(bytes_size):
    """
    Convert bytes to human readable format
    """
    if bytes_size == 0:
        return "0 B"
    
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    
    return f"{bytes_size:.1f} PB"

def clean_extracted_text(text):
    """
    Clean and normalize extracted text
    """
    if not text:
        return ""
    
    # Remove excessive whitespace
    import re
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\n\s*\n', '\n\n', text)
    
    # Remove common OCR artifacts
    text = text.replace('', '')  # Remove null characters
    text = text.replace('\x00', '')  # Remove null bytes
    
    return text.strip()
