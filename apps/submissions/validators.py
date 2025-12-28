# -*- coding: utf-8 -*-
"""
File upload validators for DOMOVIK.

This module contains validators for file uploads including:
- Extension whitelist validation
- File size validation
- MIME type validation (with actual file content inspection)
- Filename sanitization
- Unique filename generation

Security Features:
- Extension whitelist (pdf, doc, docx, xls, xlsx only)
- 10MB size limit enforcement
- MIME type verification using python-magic (inspects file content, not just headers)
- Path traversal protection in filename sanitization
- Unique filename generation to prevent collisions
"""

import os
import re
import uuid
import logging
from datetime import datetime
from django.core.exceptions import ValidationError
from django.conf import settings

# Import magic for MIME type detection
# Note: python-magic requires libmagic library (system dependency)
# On Windows: Install python-magic-bin OR fallback to content_type
try:
    import magic
    # Test if magic actually works (prevents import success but runtime failure)
    try:
        magic.from_buffer(b"test", mime=True)
        MAGIC_AVAILABLE = True
    except Exception:
        # Magic imported but libmagic not available
        MAGIC_AVAILABLE = False
except ImportError:
    MAGIC_AVAILABLE = False

# Logger for security events
logger = logging.getLogger('file_uploads')


def validate_file_extension(value):
    """
    Validate file extension against whitelist.

    Only PDF, DOC, DOCX, XLS, XLSX files are allowed (defined in settings.py).
    This is the first line of defense against dangerous file types.

    Security Rationale:
    - Extension whitelist prevents obviously dangerous files (.exe, .sh, .bat)
    - Combined with MIME validation for defense-in-depth
    - Settings-based configuration allows easy updates without code changes

    Args:
        value: UploadedFile object from Django form

    Raises:
        ValidationError: If file extension is not in allowed list (settings.ALLOWED_FILE_EXTENSIONS)

    Example:
        >>> from django.core.files.uploadedfile import SimpleUploadedFile
        >>> valid_file = SimpleUploadedFile("test.pdf", b"content")
        >>> validate_file_extension(valid_file)  # No error
        >>> invalid_file = SimpleUploadedFile("malware.exe", b"virus")
        >>> validate_file_extension(invalid_file)  # Raises ValidationError
    """
    ext = value.name.split('.')[-1].lower() if '.' in value.name else ''

    # Import from settings (DRY principle - single source of truth)
    allowed_extensions = getattr(settings, 'ALLOWED_FILE_EXTENSIONS', ['pdf', 'doc', 'docx', 'xls', 'xlsx'])

    if ext not in allowed_extensions:
        raise ValidationError(
            "Format nije podržan. Molimo koristite PDF, DOC, DOCX, XLS ili XLSX fajlove."
        )


def validate_file_size(value):
    """
    Validate file size is under maximum allowed limit (defined in settings.py).

    Security Rationale:
    - Prevents denial-of-service attacks via large file uploads
    - Protects disk space and database from excessive growth
    - Ensures reasonable performance for file processing

    Args:
        value: UploadedFile object from Django form

    Raises:
        ValidationError: If file size exceeds limit (settings.FILE_UPLOAD_MAX_MEMORY_SIZE)

    Example:
        >>> from django.core.files.uploadedfile import SimpleUploadedFile
        >>> small_file = SimpleUploadedFile("small.pdf", b"x" * 1024)  # 1KB
        >>> validate_file_size(small_file)  # No error
        >>> huge_file = SimpleUploadedFile("huge.pdf", b"x" * 20 * 1024 * 1024)  # 20MB
        >>> validate_file_size(huge_file)  # Raises ValidationError
    """
    # Import from settings (DRY principle)
    max_size = getattr(settings, 'FILE_UPLOAD_MAX_MEMORY_SIZE', 10 * 1024 * 1024)

    if value.size > max_size:
        size_mb = value.size / (1024 * 1024)
        max_size_mb = max_size / (1024 * 1024)
        raise ValidationError(
            f"Fajl premašuje {max_size_mb:.0f}MB. Maksimalna dozvoljena veličina je {max_size_mb:.0f}MB."
        )


def validate_mime_type(value):
    """
    Validate MIME type by inspecting actual file content (not just headers).

    Security Rationale:
    - Prevents extension spoofing attacks (virus.exe renamed to document.pdf)
    - Inspects first 2048 bytes of file to detect actual file type
    - Uses python-magic library (libmagic) for accurate detection
    - Defense-in-depth: Works even if client sends fake Content-Type headers

    Implementation Details:
    - Uses python-magic library if available (RECOMMENDED)
    - Falls back to Django's content_type header if magic not available
    - Logs security events when MIME validation fails (potential attack)

    Args:
        value: UploadedFile object from Django form

    Raises:
        ValidationError: If detected MIME type is not in allowed list (settings.ALLOWED_MIME_TYPES)

    Example:
        >>> # Valid PDF file
        >>> pdf_file = SimpleUploadedFile("doc.pdf", b"%PDF-1.4...")
        >>> validate_mime_type(pdf_file)  # No error
        >>> # Malicious file: virus.exe renamed to document.pdf
        >>> fake_pdf = SimpleUploadedFile("virus.pdf", b"MZ\\x90\\x00...")  # EXE header
        >>> validate_mime_type(fake_pdf)  # Raises ValidationError + logs security event
    """
    # Import allowed MIME types from settings (DRY principle)
    allowed_mimes = getattr(settings, 'ALLOWED_MIME_TYPES', {
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    })

    detected_mime = None

    # Method 1: Use python-magic to inspect actual file content (PREFERRED)
    if MAGIC_AVAILABLE:
        try:
            # Read first 2048 bytes of file for MIME detection
            value.seek(0)  # Reset file pointer to beginning
            file_header = value.read(2048)
            value.seek(0)  # Reset again for later processing

            # Detect MIME type from file content
            detected_mime = magic.from_buffer(file_header, mime=True)

        except Exception as e:
            # Log magic detection failure but continue with fallback
            logger.warning(f"python-magic MIME detection failed for {value.name}: {e}")

    # Method 2: Fallback to Django's content_type (client-provided, less secure)
    if not detected_mime:
        detected_mime = value.content_type
        logger.info(f"Using fallback MIME detection (content_type header) for {value.name}: {detected_mime}")

    # Validate MIME type
    if detected_mime not in allowed_mimes:
        # Log security event - potential attack attempt
        logger.warning(
            f"MIME validation FAILED for {value.name}: "
            f"detected={detected_mime}, allowed={allowed_mimes}"
        )

        raise ValidationError(
            "Fajl nije validan. Molimo proverite da je fajl zaista PDF, DOC, DOCX, XLS ili XLSX format."
        )


def sanitize_filename(filename):
    """
    Sanitize filename by removing dangerous characters.

    Removes:
    - Path traversal sequences (../, //, backslashes)
    - Special characters except Serbian letters, alphanumeric, dots, dashes, underscores
    - Leading/trailing whitespace and dots

    Preserves:
    - Serbian characters: č, ć, š, đ, ž, Č, Ć, Š, Đ, Ž
    - Alphanumeric characters
    - Dots, dashes, underscores
    - Spaces (converted to underscores)

    Args:
        filename: Original filename

    Returns:
        str: Sanitized filename
    """
    # Remove path components
    filename = os.path.basename(filename)

    # Split into name and extension
    name_parts = filename.rsplit('.', 1)
    base_name = name_parts[0] if len(name_parts) > 0 else filename
    extension = name_parts[1] if len(name_parts) > 1 else ''

    # Remove dangerous characters, keep Serbian letters
    # Pattern: Keep word characters, spaces, Serbian letters, dots, dashes, underscores
    safe_base = re.sub(r'[^\w\sčćšđžČĆŠĐŽ._-]', '', base_name, flags=re.UNICODE)

    # Replace spaces with underscores
    safe_base = safe_base.replace(' ', '_')

    # Remove multiple consecutive underscores/dashes
    safe_base = re.sub(r'[_-]+', '_', safe_base)

    # Remove leading/trailing underscores, dashes, dots
    safe_base = safe_base.strip('._- ')

    # Limit length (leave room for timestamp + UUID prefix)
    max_base_length = 100
    if len(safe_base) > max_base_length:
        safe_base = safe_base[:max_base_length]

    # Reconstruct filename
    if extension:
        return f"{safe_base}.{extension.lower()}"
    else:
        return safe_base


def generate_unique_filename(original_filename):
    """
    Generate unique filename with timestamp and UUID.

    Format: {timestamp}_{uuid}_{sanitized_original}.{ext}
    Example: 20250127_143022_abc12345_budzet_projekta.pdf

    This prevents:
    - Filename collisions
    - Overwriting existing files
    - Guessing filenames for unauthorized access

    Args:
        original_filename: Original filename from user

    Returns:
        str: Unique filename for storage
    """
    # Sanitize original filename
    sanitized = sanitize_filename(original_filename)

    # Split into name and extension
    if '.' in sanitized:
        base_name, extension = sanitized.rsplit('.', 1)
    else:
        base_name = sanitized
        extension = ''

    # Generate timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Generate short UUID
    unique_id = uuid.uuid4().hex[:8]

    # Construct unique filename
    if extension:
        return f"{timestamp}_{unique_id}_{base_name}.{extension}"
    else:
        return f"{timestamp}_{unique_id}_{base_name}"


def validate_email(email):
    """
    Validate email address format.

    Args:
        email (str): Email address to validate

    Raises:
        ValidationError: If email format is invalid
    """
    if not email:
        raise ValidationError('Email adresa je obavezna.')

    # Basic email regex pattern
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        raise ValidationError('Molimo unesite validnu email adresu.')


def validate_phone(phone):
    """
    Validate Serbian phone number format.

    Accepts formats:
    - +381XXXXXXXXX (international)
    - 06XXXXXXXX (mobile)
    - 0XXXXXXXX (landline)

    Args:
        phone (str): Phone number to validate

    Raises:
        ValidationError: If phone format is invalid
    """
    if not phone:
        raise ValidationError('Broj telefona je obavezan.')

    # Remove spaces and dashes
    cleaned_phone = phone.replace(' ', '').replace('-', '')

    # Serbian phone pattern: +381 or 0, followed by 8-10 digits
    phone_pattern = r'^(\+381|0)[0-9]{8,10}$'
    if not re.match(phone_pattern, cleaned_phone):
        raise ValidationError('Molimo unesite validan broj telefona (npr. +381XXXXXXXXX ili 06XXXXXXXX).')


def validate_jmbg(jmbg):
    """
    Validate Serbian JMBG (Unique Master Citizen Number).

    JMBG format: 13 digits (DDMMYYYRRBBBC)
    - DD: day of birth (01-31)
    - MM: month of birth (01-12)
    - YYY: year of birth (last 3 digits)
    - RR: region code
    - BBB: birth sequence
    - C: control digit

    Args:
        jmbg (str): JMBG to validate

    Raises:
        ValidationError: If JMBG format is invalid
    """
    if not jmbg:
        return  # JMBG is optional in some cases

    # Must be exactly 13 digits
    if not re.match(r'^\d{13}$', jmbg):
        raise ValidationError('JMBG mora imati tačno 13 cifara.')

    # Validate day (01-31)
    day = int(jmbg[0:2])
    if day < 1 or day > 31:
        raise ValidationError('JMBG sadrži neispravan dan rođenja.')

    # Validate month (01-12)
    month = int(jmbg[2:4])
    if month < 1 or month > 12:
        raise ValidationError('JMBG sadrži neispravan mesec rođenja.')


def validate_maticni_broj(maticni_broj):
    """
    Validate Serbian Matični Broj (Company Registration Number).

    Format: 8 digits

    Args:
        maticni_broj (str): Matični broj to validate

    Raises:
        ValidationError: If matični broj format is invalid
    """
    if not maticni_broj:
        return  # Matični broj is optional in some cases

    # Must be exactly 8 digits
    if not re.match(r'^\d{8}$', maticni_broj):
        raise ValidationError('Matični broj mora imati tačno 8 cifara.')


# Export list for module
__all__ = [
    'validate_file_extension',
    'validate_file_size',
    'validate_mime_type',
    'sanitize_filename',
    'generate_unique_filename',
    'validate_email',
    'validate_phone',
    'validate_jmbg',
    'validate_maticni_broj',
]
