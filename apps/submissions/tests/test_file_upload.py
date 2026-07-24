# -*- coding: utf-8 -*-
"""
Integration tests for file upload/delete functionality.
Story 2.8: File Upload Infrastructure

Tests:
- Upload valid files via POST to /api/files/upload/
- Upload oversized files (rejected with 400)
- Upload invalid extensions (rejected with 400)
- Upload without CSRF token (rejected with 403)
- Delete file via POST to /api/files/delete/<id>/
- Delete non-existent file (404)
- Delete another session's file (403)
- Physical file saved to media/uploads/drafts/
- Database record created
"""
import os
from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from apps.submissions.models import UploadedFile


class FileUploadViewTests(TestCase):
    """Integration tests for file upload view."""

    def setUp(self):
        """Set up test client and session."""
        self.client = Client()
        # Enable CSRF for testing
        self.client = Client(enforce_csrf_checks=True)
        # Create session
        session = self.client.session
        session.save()

    def test_upload_valid_pdf_file(self):
        """Should successfully upload valid PDF file."""
        # Create test PDF file
        file_content = b'PDF content here'
        uploaded_file = SimpleUploadedFile(
            'test_budzet.pdf',
            file_content,
            content_type='application/pdf'
        )

        # Get CSRF token
        response = self.client.get(reverse('submissions:coa_form'))
        csrf_token = response.cookies.get('csrftoken').value

        # Upload file
        response = self.client.post(
            '/api/files/upload/',
            {
                'file': uploaded_file,
                'category': 'BUDGET',
                'csrfmiddlewaretoken': csrf_token
            },
            HTTP_X_CSRFTOKEN=csrf_token
        )

        # Assertions
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('file_id', data)
        self.assertIn('filename', data)
        self.assertEqual(data['filename'], 'test_budzet.pdf')

        # Verify database record
        file_record = UploadedFile.objects.get(id=data['file_id'])
        self.assertEqual(file_record.original_filename, 'test_budzet.pdf')
        self.assertEqual(file_record.file_type, 'pdf')
        self.assertEqual(file_record.category, 'BUDGET')

    def test_upload_valid_doc_file(self):
        """Should successfully upload valid DOC file."""
        file_content = b'DOC content'
        uploaded_file = SimpleUploadedFile(
            'biografija.doc',
            file_content,
            content_type='application/msword'
        )

        response = self.client.get(reverse('submissions:coa_form'))
        csrf_token = response.cookies.get('csrftoken').value

        response = self.client.post(
            '/api/files/upload/',
            {
                'file': uploaded_file,
                'category': 'BIOGRAPHY',
                'csrfmiddlewaretoken': csrf_token
            },
            HTTP_X_CSRFTOKEN=csrf_token
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])

    def test_upload_valid_xlsx_file(self):
        """Should successfully upload valid XLSX file."""
        file_content = b'XLSX content'
        uploaded_file = SimpleUploadedFile(
            'tabela.xlsx',
            file_content,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

        response = self.client.get(reverse('submissions:coa_form'))
        csrf_token = response.cookies.get('csrftoken').value

        response = self.client.post(
            '/api/files/upload/',
            {
                'file': uploaded_file,
                'category': 'SUPPORT_LETTER',
                'csrfmiddlewaretoken': csrf_token
            },
            HTTP_X_CSRFTOKEN=csrf_token
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])

    def test_upload_oversized_file_rejected(self):
        """Should reject file over 10MB with 400 error."""
        # Create 11MB file
        size_11mb = 11 * 1024 * 1024
        file_content = b'x' * size_11mb
        uploaded_file = SimpleUploadedFile(
            'huge.pdf',
            file_content,
            content_type='application/pdf'
        )

        response = self.client.get(reverse('submissions:coa_form'))
        csrf_token = response.cookies.get('csrftoken').value

        response = self.client.post(
            '/api/files/upload/',
            {
                'file': uploaded_file,
                'category': 'BUDGET',
                'csrfmiddlewaretoken': csrf_token
            },
            HTTP_X_CSRFTOKEN=csrf_token
        )

        # Should reject with 400
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('errors', data)

    def test_upload_invalid_extension_rejected(self):
        """Should reject file with invalid extension (e.g., .exe)."""
        file_content = b'EXE content'
        uploaded_file = SimpleUploadedFile(
            'virus.exe',
            file_content,
            content_type='application/x-msdownload'
        )

        response = self.client.get(reverse('submissions:coa_form'))
        csrf_token = response.cookies.get('csrftoken').value

        response = self.client.post(
            '/api/files/upload/',
            {
                'file': uploaded_file,
                'category': 'BUDGET',
                'csrfmiddlewaretoken': csrf_token
            },
            HTTP_X_CSRFTOKEN=csrf_token
        )

        # Should reject with 400
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])

    def test_upload_without_csrf_token_rejected(self):
        """Should reject upload without CSRF token (403)."""
        file_content = b'PDF content'
        uploaded_file = SimpleUploadedFile(
            'test.pdf',
            file_content,
            content_type='application/pdf'
        )

        # Upload without CSRF token
        response = self.client.post(
            '/api/files/upload/',
            {
                'file': uploaded_file,
                'category': 'BUDGET'
            }
        )

        # Should reject with 403
        self.assertEqual(response.status_code, 403)

    def test_upload_creates_database_record(self):
        """Should create database record with correct metadata."""
        file_content = b'PDF content'
        uploaded_file = SimpleUploadedFile(
            'test_record.pdf',
            file_content,
            content_type='application/pdf'
        )

        response = self.client.get(reverse('submissions:coa_form'))
        csrf_token = response.cookies.get('csrftoken').value

        response = self.client.post(
            '/api/files/upload/',
            {
                'file': uploaded_file,
                'category': 'BUDGET',
                'csrfmiddlewaretoken': csrf_token
            },
            HTTP_X_CSRFTOKEN=csrf_token
        )

        data = response.json()
        file_id = data['file_id']

        # Verify database record
        file_record = UploadedFile.objects.get(id=file_id)
        self.assertEqual(file_record.original_filename, 'test_record.pdf')
        self.assertEqual(file_record.file_size, len(file_content))
        self.assertEqual(file_record.file_type, 'pdf')
        self.assertEqual(file_record.category, 'BUDGET')
        self.assertFalse(file_record.is_deleted)
        self.assertIsNotNone(file_record.uploaded_by_session)


class FileDeleteViewTests(TestCase):
    """Integration tests for file delete view."""

    def setUp(self):
        """Set up test client and create test file."""
        self.client = Client(enforce_csrf_checks=True)
        session = self.client.session
        session.save()

        # Create test file in database
        self.test_file = UploadedFile.objects.create(
            original_filename='test_delete.pdf',
            stored_filename='20250127_abc123_test_delete.pdf',
            file_path='uploads/drafts/20250127_abc123_test_delete.pdf',
            file_size=1024,
            file_type='pdf',
            mime_type='application/pdf',
            category='BUDGET',
            uploaded_by_session=session.session_key
        )

    def test_delete_file_successfully(self):
        """Should successfully delete file."""
        response = self.client.get(reverse('submissions:coa_form'))
        csrf_token = response.cookies.get('csrftoken').value

        response = self.client.post(
            f'/api/files/delete/{self.test_file.id}/',
            {'csrfmiddlewaretoken': csrf_token},
            HTTP_X_CSRFTOKEN=csrf_token
        )

        # Assertions
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])

        # Verify soft delete
        self.test_file.refresh_from_db()
        self.assertTrue(self.test_file.is_deleted)

    def test_delete_non_existent_file(self):
        """Should return 404 for non-existent file."""
        response = self.client.get(reverse('submissions:coa_form'))
        csrf_token = response.cookies.get('csrftoken').value

        response = self.client.post(
            '/api/files/delete/99999/',
            {'csrfmiddlewaretoken': csrf_token},
            HTTP_X_CSRFTOKEN=csrf_token
        )

        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertFalse(data['success'])

    def test_delete_another_session_file_rejected(self):
        """Should reject deletion of file from another session (403)."""
        # Create file with different session
        other_file = UploadedFile.objects.create(
            original_filename='other.pdf',
            stored_filename='20250127_xyz789_other.pdf',
            file_path='uploads/drafts/20250127_xyz789_other.pdf',
            file_size=1024,
            file_type='pdf',
            mime_type='application/pdf',
            category='BUDGET',
            uploaded_by_session='different_session_key_12345'
        )

        response = self.client.get(reverse('submissions:coa_form'))
        csrf_token = response.cookies.get('csrftoken').value

        response = self.client.post(
            f'/api/files/delete/{other_file.id}/',
            {'csrfmiddlewaretoken': csrf_token},
            HTTP_X_CSRFTOKEN=csrf_token
        )

        # Should reject with 403
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('dozvolu', data['error'])

    def test_delete_without_csrf_token_rejected(self):
        """Should reject deletion without CSRF token (403)."""
        response = self.client.post(f'/api/files/delete/{self.test_file.id}/')
        self.assertEqual(response.status_code, 403)
