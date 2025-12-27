# -*- coding: utf-8 -*-
"""
Unit tests for file upload validators.
Story 2.8: File Upload Infrastructure

Tests:
- validate_file_extension() with valid/invalid extensions
- validate_file_size() with files under/over 10MB
- validate_mime_type() with correct/spoofed MIME types
- sanitize_filename() removes dangerous characters
- generate_unique_filename() prevents collisions
"""
import io
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from apps.submissions.validators import (
    validate_file_extension,
    validate_file_size,
    validate_mime_type,
    sanitize_filename,
    generate_unique_filename
)

# Import file size limit from settings (DRY principle)
FILE_UPLOAD_MAX_SIZE = settings.FILE_UPLOAD_MAX_MEMORY_SIZE


class FileExtensionValidatorTests(TestCase):
    """Test validate_file_extension() function."""

    def test_valid_pdf_extension(self):
        """PDF extension should be accepted."""
        file = SimpleUploadedFile('test.pdf', b'content', content_type='application/pdf')
        # Should not raise ValidationError
        validate_file_extension(file)

    def test_valid_doc_extension(self):
        """DOC extension should be accepted."""
        file = SimpleUploadedFile('test.doc', b'content', content_type='application/msword')
        validate_file_extension(file)

    def test_valid_docx_extension(self):
        """DOCX extension should be accepted."""
        file = SimpleUploadedFile(
            'test.docx',
            b'content',
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        validate_file_extension(file)

    def test_valid_xls_extension(self):
        """XLS extension should be accepted."""
        file = SimpleUploadedFile('test.xls', b'content', content_type='application/vnd.ms-excel')
        validate_file_extension(file)

    def test_valid_xlsx_extension(self):
        """XLSX extension should be accepted."""
        file = SimpleUploadedFile(
            'test.xlsx',
            b'content',
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        validate_file_extension(file)

    def test_invalid_exe_extension(self):
        """EXE extension should be rejected."""
        file = SimpleUploadedFile('virus.exe', b'content', content_type='application/x-msdownload')
        with self.assertRaises(ValidationError) as cm:
            validate_file_extension(file)
        self.assertIn('Format nije podržan', str(cm.exception))

    def test_invalid_txt_extension(self):
        """TXT extension should be rejected."""
        file = SimpleUploadedFile('test.txt', b'content', content_type='text/plain')
        with self.assertRaises(ValidationError) as cm:
            validate_file_extension(file)
        self.assertIn('Format nije podržan', str(cm.exception))

    def test_invalid_zip_extension(self):
        """ZIP extension should be rejected."""
        file = SimpleUploadedFile('archive.zip', b'content', content_type='application/zip')
        with self.assertRaises(ValidationError) as cm:
            validate_file_extension(file)
        self.assertIn('Format nije podržan', str(cm.exception))

    def test_case_insensitive_validation(self):
        """Extension validation should be case-insensitive."""
        file = SimpleUploadedFile('TEST.PDF', b'content', content_type='application/pdf')
        # Should not raise ValidationError
        validate_file_extension(file)


class FileSizeValidatorTests(TestCase):
    """Test validate_file_size() function."""

    def test_accept_small_file(self):
        """File under 10MB should be accepted."""
        # 5MB file
        size_5mb = 5 * 1024 * 1024
        content = b'x' * size_5mb
        file = SimpleUploadedFile('test.pdf', content, content_type='application/pdf')
        # Should not raise ValidationError
        validate_file_size(file)

    def test_accept_exactly_10mb(self):
        """File exactly 10MB should be accepted."""
        size_10mb = FILE_UPLOAD_MAX_SIZE
        content = b'x' * size_10mb
        file = SimpleUploadedFile('test.pdf', content, content_type='application/pdf')
        # Should not raise ValidationError
        validate_file_size(file)

    def test_reject_oversized_file(self):
        """File over 10MB should be rejected."""
        # 11MB file
        size_11mb = 11 * 1024 * 1024
        content = b'x' * size_11mb
        file = SimpleUploadedFile('big.pdf', content, content_type='application/pdf')
        with self.assertRaises(ValidationError) as cm:
            validate_file_size(file)
        self.assertIn('premašuje 10MB', str(cm.exception))

    def test_accept_tiny_file(self):
        """Tiny file (1KB) should be accepted."""
        content = b'x' * 1024
        file = SimpleUploadedFile('tiny.pdf', content, content_type='application/pdf')
        # Should not raise ValidationError
        validate_file_size(file)


class MimeTypeValidatorTests(TestCase):
    """Test validate_mime_type() function."""

    def test_accept_valid_pdf_mime(self):
        """Valid PDF MIME type should be accepted."""
        file = SimpleUploadedFile('test.pdf', b'content', content_type='application/pdf')
        # Should not raise ValidationError
        validate_mime_type(file)

    def test_accept_valid_doc_mime(self):
        """Valid DOC MIME type should be accepted."""
        file = SimpleUploadedFile('test.doc', b'content', content_type='application/msword')
        validate_mime_type(file)

    def test_accept_valid_docx_mime(self):
        """Valid DOCX MIME type should be accepted."""
        file = SimpleUploadedFile(
            'test.docx',
            b'content',
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        validate_mime_type(file)

    def test_accept_valid_xls_mime(self):
        """Valid XLS MIME type should be accepted."""
        file = SimpleUploadedFile('test.xls', b'content', content_type='application/vnd.ms-excel')
        validate_mime_type(file)

    def test_accept_valid_xlsx_mime(self):
        """Valid XLSX MIME type should be accepted."""
        file = SimpleUploadedFile(
            'test.xlsx',
            b'content',
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        validate_mime_type(file)

    def test_reject_invalid_mime_type(self):
        """Invalid MIME type should be rejected."""
        # Text file with wrong MIME type
        file = SimpleUploadedFile('fake.pdf', b'content', content_type='text/plain')
        with self.assertRaises(ValidationError) as cm:
            validate_mime_type(file)
        self.assertIn('nije validan', str(cm.exception))

    def test_reject_executable_mime_type(self):
        """Executable MIME type should be rejected."""
        file = SimpleUploadedFile('virus.pdf', b'content', content_type='application/x-msdownload')
        with self.assertRaises(ValidationError) as cm:
            validate_mime_type(file)
        self.assertIn('nije validan', str(cm.exception))


class SanitizeFilenameTests(TestCase):
    """Test sanitize_filename() function."""

    def test_sanitize_removes_path_traversal(self):
        """Should remove path traversal sequences."""
        result = sanitize_filename('../../etc/passwd')
        self.assertNotIn('..', result)
        self.assertNotIn('/', result)

    def test_sanitize_preserves_serbian_characters(self):
        """Should preserve Serbian characters (č, ć, š, đ, ž)."""
        result = sanitize_filename('budžet_projekta_čačak.pdf')
        self.assertIn('budžet', result)
        self.assertIn('čačak', result)

    def test_sanitize_removes_special_characters(self):
        """Should remove dangerous special characters."""
        result = sanitize_filename('test<>:"|?*.pdf')
        # Should only have alphanumeric and allowed characters
        self.assertNotIn('<', result)
        self.assertNotIn('>', result)
        self.assertNotIn(':', result)
        self.assertNotIn('"', result)
        self.assertNotIn('|', result)
        self.assertNotIn('?', result)

    def test_sanitize_replaces_spaces_with_underscores(self):
        """Should replace spaces with underscores."""
        result = sanitize_filename('my test file.pdf')
        self.assertIn('my_test_file', result)

    def test_sanitize_preserves_extension(self):
        """Should preserve file extension."""
        result = sanitize_filename('document.pdf')
        self.assertTrue(result.endswith('.pdf'))

    def test_sanitize_limits_length(self):
        """Should limit filename length."""
        long_name = 'a' * 200 + '.pdf'
        result = sanitize_filename(long_name)
        # Should be shorter than original
        self.assertLess(len(result), len(long_name))


class GenerateUniqueFilenameTests(TestCase):
    """Test generate_unique_filename() function."""

    def test_generates_unique_filename(self):
        """Should generate unique filename with timestamp and UUID."""
        result = generate_unique_filename('test.pdf')
        # Should contain timestamp pattern (YYYYMMDD_HHMMSS)
        self.assertRegex(result, r'\d{8}_\d{6}')
        # Should contain original filename
        self.assertIn('test', result)
        # Should end with .pdf
        self.assertTrue(result.endswith('.pdf'))

    def test_generates_different_filenames(self):
        """Should generate different filenames for same input."""
        result1 = generate_unique_filename('test.pdf')
        result2 = generate_unique_filename('test.pdf')
        # Should be different due to UUID
        self.assertNotEqual(result1, result2)

    def test_handles_serbian_characters(self):
        """Should handle Serbian characters in filename."""
        result = generate_unique_filename('budžet.pdf')
        self.assertIn('budžet', result)

    def test_sanitizes_dangerous_characters(self):
        """Should sanitize dangerous characters."""
        result = generate_unique_filename('../../virus.pdf')
        self.assertNotIn('..', result)
        self.assertNotIn('/', result)
