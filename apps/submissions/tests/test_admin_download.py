# -*- coding: utf-8 -*-
"""
Unit tests for admin file download functionality - Story 4.4.

Tests cover:
- Individual file download
- Bulk ZIP download
- Authorization checks
- Error handling (missing files, wrong application)
- FileMetadataInline download links
- Download All Documents button visibility
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.conf import settings
from apps.submissions.models import Application, Applicant, ProjectData, FileMetadata
import os
import time
import tempfile


class AdminFileDownloadTests(TestCase):
    """Test admin file download functionality - Story 4.4."""

    def setUp(self):
        """Create test admin, application, and files."""
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username='testadmin',
            email='testadmin@domovik.local',
            password='TestAdmin123!'
        )

        # Create COA application first (Applicant requires application)
        self.application = Application.objects.create(
            reference_number='COA-2025-001',
            application_type='COA',
            status='submitted',
        )

        # Create Applicant linked to application
        self.applicant = Applicant.objects.create(
            application=self.application,
            entity_type='fizicko',
            first_name='Test',
            last_name='User',
            jmbg='1234567890123',
            address='Test Address',
            email='test@example.com',
            phone='+381601234567',
        )

        # Link applicant back to application
        self.application.applicant = self.applicant
        self.application.save()

        ProjectData.objects.create(
            application=self.application,
            title='Test Projekat',
            short_description='Opis',
            problem='Problem',
            main_goal='Cilj',
            specific_goals='Ciljevi',
            target_groups='Grupe',
            activities='Aktivnosti',
            results='Rezultati',
            total_budget=100000,
        )

        # Create test files on disk
        self.test_file_path = os.path.join(
            settings.MEDIA_ROOT,
            'submissions',
            'budgets',
            'COA-2025-001_budzet_test.xlsx'
        )

        # Ensure directory exists
        os.makedirs(os.path.dirname(self.test_file_path), exist_ok=True)

        # Create test file
        with open(self.test_file_path, 'wb') as f:
            f.write(b'Test file content')

        # Create FileMetadata
        # BUGFIX: Use 'BUDGET' (English) not 'BUDZET' (Serbian)
        self.file_metadata = FileMetadata.objects.create(
            application=self.application,
            file_type='BUDGET',
            original_filename='Budzet_Projekta_2025.xlsx',
            stored_filename='COA-2025-001_budzet_test.xlsx',
            file_size=1000,
        )

    def tearDown(self):
        """Clean up test files."""
        # Small delay to allow Windows to release file locks
        time.sleep(0.1)

        if os.path.exists(self.test_file_path):
            try:
                os.remove(self.test_file_path)
            except PermissionError:
                # File still locked, wait and retry
                time.sleep(0.2)
                try:
                    os.remove(self.test_file_path)
                except PermissionError:
                    pass  # Let test database cleanup handle it

    def test_download_file_requires_admin_auth(self):
        """Test download file view requires admin authentication."""
        # Not logged in
        url = reverse('submissions:admin_download_file', args=[self.application.id, self.file_metadata.id])
        response = self.client.get(url)

        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response.url)

    def test_download_file_success(self):
        """Test admin can download file successfully."""
        self.client.login(username='testadmin', password='TestAdmin123!')

        url = reverse('submissions:admin_download_file', args=[self.application.id, self.file_metadata.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        self.assertIn('attachment', response['Content-Disposition'])
        self.assertIn('Budzet_Projekta_2025.xlsx', response['Content-Disposition'])

    def test_download_file_wrong_application(self):
        """Test download fails if file doesn't belong to application."""
        # Create another application
        another_app = Application.objects.create(
            reference_number='COA-2025-002',
            application_type='COA',
            status='submitted',
        )

        # Create another applicant for this application
        another_applicant = Applicant.objects.create(
            application=another_app,
            entity_type='fizicko',
            first_name='Other',
            last_name='User',
            jmbg='9876543210987',
            address='Other Address',
            email='other@example.com',
            phone='+381609876543',
        )

        another_app.applicant = another_applicant
        another_app.save()

        self.client.login(username='testadmin', password='TestAdmin123!')

        # Try to download file from wrong application
        url = reverse('submissions:admin_download_file', args=[another_app.id, self.file_metadata.id])
        response = self.client.get(url)

        # Should return 403 Forbidden
        self.assertEqual(response.status_code, 403)

    def test_download_file_not_found_on_disk(self):
        """Test download fails gracefully if file missing from disk."""
        # Delete file from disk
        os.remove(self.test_file_path)

        self.client.login(username='testadmin', password='TestAdmin123!')

        url = reverse('submissions:admin_download_file', args=[self.application.id, self.file_metadata.id])
        response = self.client.get(url)

        # Should return 404
        self.assertEqual(response.status_code, 404)

    def test_download_all_files_requires_admin_auth(self):
        """Test download all files view requires admin authentication."""
        url = reverse('submissions:admin_download_all', args=[self.application.id])
        response = self.client.get(url)

        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response.url)

    def test_download_all_files_success(self):
        """Test admin can download all files as ZIP."""
        self.client.login(username='testadmin', password='TestAdmin123!')

        url = reverse('submissions:admin_download_all', args=[self.application.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/zip')
        self.assertIn('attachment', response['Content-Disposition'])
        self.assertIn('COA-2025-001_documents.zip', response['Content-Disposition'])

    def test_download_all_files_no_files(self):
        """Test download all returns 404 if application has no files."""
        # Delete file metadata
        self.file_metadata.delete()

        self.client.login(username='testadmin', password='TestAdmin123!')

        url = reverse('submissions:admin_download_all', args=[self.application.id])
        response = self.client.get(url)

        # Should return 404
        self.assertEqual(response.status_code, 404)

    def test_download_link_in_inline(self):
        """Test download link appears in FileMetadata inline."""
        self.client.login(username='testadmin', password='TestAdmin123!')

        # Navigate to detail view
        response = self.client.get(f'/admin/submissions/application/{self.application.id}/change/')

        self.assertEqual(response.status_code, 200)
        # Verify download link present
        self.assertContains(response, '⬇️ Download')
        self.assertContains(response, 'admin/application')
        self.assertContains(response, 'download-file')

    def test_download_all_button_in_detail_view(self):
        """Test "Download All Documents" button appears in detail view."""
        self.client.login(username='testadmin', password='TestAdmin123!')

        response = self.client.get(f'/admin/submissions/application/{self.application.id}/change/')

        self.assertEqual(response.status_code, 200)
        # Verify download all button present
        self.assertContains(response, 'Download All Documents')
        self.assertContains(response, 'ZIP')
        self.assertContains(response, 'download-all')

    def test_download_all_button_hidden_if_no_files(self):
        """Test "Download All Documents" button hidden if no files."""
        # Delete file metadata
        self.file_metadata.delete()

        self.client.login(username='testadmin', password='TestAdmin123!')

        response = self.client.get(f'/admin/submissions/application/{self.application.id}/change/')

        self.assertEqual(response.status_code, 200)
        # Verify download all button NOT present
        self.assertNotContains(response, 'Download All Documents')

    def test_missing_file_logs_error(self):
        """
        Test logger.error() is called when file not found on disk.
        CODE REVIEW FIX - ISSUE 10: Story requirement (line 1416) - verify logging.
        """
        import logging
        from unittest.mock import patch

        # Delete file from disk
        os.remove(self.test_file_path)

        self.client.login(username='testadmin', password='TestAdmin123!')

        # Patch logger to verify error logging
        with patch('apps.submissions.views.logger') as mock_logger:
            url = reverse('submissions:admin_download_file', args=[self.application.id, self.file_metadata.id])
            response = self.client.get(url)

            # Verify 404 response
            self.assertEqual(response.status_code, 404)

            # Verify logger.error() was called with file path information
            mock_logger.error.assert_called_once()
            error_call_args = mock_logger.error.call_args[0][0]
            self.assertIn('File not found', error_call_args)
            self.assertIn('COA-2025-001', error_call_args)

    def test_bug_regression_file_category_folder_mapping(self):
        """
        BUGFIX REGRESSION TEST: FILE_CATEGORY_FOLDERS must map English keys (BUDGET, BIOGRAPHY, SUPPORT_LETTER).

        BUG #1: 404 Error on Individual File Download
        ROOT CAUSE: FILE_CATEGORY_FOLDERS had Serbian keys ('BUDZET') but database has English ('BUDGET')
        IMPACT: .get('BUDGET', 'submissions') returned 'submissions' causing path:
                media/submissions/submissions/file.xlsx instead of media/submissions/budgets/file.xlsx
        FIX: Updated constants.py to use English keys matching FileType constants
        """
        from apps.submissions.constants import FILE_CATEGORY_FOLDERS, FileType

        # Verify all FileType constants have corresponding folder mappings
        self.assertIn(FileType.BUDGET, FILE_CATEGORY_FOLDERS)
        self.assertIn(FileType.BIOGRAPHY, FILE_CATEGORY_FOLDERS)
        self.assertIn(FileType.SUPPORT_LETTER, FILE_CATEGORY_FOLDERS)
        self.assertIn(FileType.OPIS_INICIJATIVE, FILE_CATEGORY_FOLDERS)
        self.assertIn(FileType.PISMO_NAMERE, FILE_CATEGORY_FOLDERS)

        # Verify correct folder mappings
        self.assertEqual(FILE_CATEGORY_FOLDERS[FileType.BUDGET], 'budgets')
        self.assertEqual(FILE_CATEGORY_FOLDERS[FileType.BIOGRAPHY], 'biographies')
        self.assertEqual(FILE_CATEGORY_FOLDERS[FileType.SUPPORT_LETTER], 'letters_of_support')
        self.assertEqual(FILE_CATEGORY_FOLDERS[FileType.OPIS_INICIJATIVE], 'initiative_descriptions')
        self.assertEqual(FILE_CATEGORY_FOLDERS[FileType.PISMO_NAMERE], 'letters_of_intent')

        # Verify Serbian keys do NOT exist (regression prevention)
        self.assertNotIn('BUDZET', FILE_CATEGORY_FOLDERS)
        self.assertNotIn('BIOGRAFIJA', FILE_CATEGORY_FOLDERS)
        self.assertNotIn('PISMO_PODRSKE', FILE_CATEGORY_FOLDERS)

    def test_bug_regression_download_file_from_drafts_folder(self):
        """
        BUGFIX REGRESSION TEST: Download should work for files still in drafts folder.

        BUG #1 & #2: Files not moved from uploads/drafts/ to submissions/{category}/ after submission
        ROOT CAUSE: No file migration logic in process_submission()
        IMPACT:
        - BUG #1: 404 error on individual download
        - BUG #2: Empty ZIP file (files not found)
        FIX: Updated download_file() and download_all_files() to check drafts folder as fallback
        """
        # Create file in drafts folder (simulating unmoved file after submission)
        drafts_file_path = os.path.join(
            settings.MEDIA_ROOT,
            'uploads',
            'drafts',
            'test_drafts_file.xlsx'
        )

        os.makedirs(os.path.dirname(drafts_file_path), exist_ok=True)
        with open(drafts_file_path, 'wb') as f:
            f.write(b'Test drafts file content')

        # Create FileMetadata pointing to this file
        drafts_file_metadata = FileMetadata.objects.create(
            application=self.application,
            file_type='BIOGRAPHY',
            original_filename='Biografija_Test.xlsx',
            stored_filename='test_drafts_file.xlsx',
            file_size=500,
        )

        self.client.login(username='testadmin', password='TestAdmin123!')

        try:
            # Test individual download works with file in drafts
            url = reverse('submissions:admin_download_file', args=[self.application.id, drafts_file_metadata.id])
            response = self.client.get(url)

            self.assertEqual(response.status_code, 200,
                "Download should succeed even if file in drafts folder")
            self.assertEqual(response['Content-Type'],
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            self.assertIn('Biografija_Test.xlsx', response['Content-Disposition'])

        finally:
            # Cleanup (Windows-safe with retry)
            time.sleep(0.1)
            if os.path.exists(drafts_file_path):
                try:
                    os.remove(drafts_file_path)
                except PermissionError:
                    time.sleep(0.2)
                    try:
                        os.remove(drafts_file_path)
                    except PermissionError:
                        pass  # Let test database cleanup handle it

    def test_bug_regression_download_all_includes_drafts_files(self):
        """
        BUGFIX REGRESSION TEST: ZIP download should include files from drafts folder.

        BUG #2: Empty ZIP File
        ROOT CAUSE: Files in drafts folder not found, ZIP created but empty
        FIX: Updated download_all_files() to check drafts folder for each file
        """
        import zipfile
        from io import BytesIO

        # Create file in drafts folder
        drafts_file_path = os.path.join(
            settings.MEDIA_ROOT,
            'uploads',
            'drafts',
            'test_bio_drafts.pdf'
        )

        os.makedirs(os.path.dirname(drafts_file_path), exist_ok=True)
        with open(drafts_file_path, 'wb') as f:
            f.write(b'Biography PDF content')

        # Create FileMetadata for drafts file
        drafts_file = FileMetadata.objects.create(
            application=self.application,
            file_type='BIOGRAPHY',
            original_filename='Biografija_Drafts.pdf',
            stored_filename='test_bio_drafts.pdf',
            file_size=200,
        )

        self.client.login(username='testadmin', password='TestAdmin123!')

        try:
            # Download ZIP
            url = reverse('submissions:admin_download_all', args=[self.application.id])
            response = self.client.get(url)

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response['Content-Type'], 'application/zip')

            # Verify ZIP contains files from both locations (final + drafts)
            zip_content = BytesIO(response.content)
            with zipfile.ZipFile(zip_content, 'r') as zip_file:
                file_list = zip_file.namelist()

                # Should contain file from final location (budgets)
                self.assertIn('Budzet_Projekta_2025.xlsx', file_list,
                    "ZIP should include file from final location")

                # Should contain file from drafts location
                self.assertIn('Biografija_Drafts.pdf', file_list,
                    "ZIP should include file from drafts folder")

                # Verify ZIP is not empty
                self.assertGreater(len(file_list), 0,
                    "ZIP should not be empty when files exist in drafts")

        finally:
            # Cleanup (Windows-safe with retry)
            time.sleep(0.1)
            if os.path.exists(drafts_file_path):
                try:
                    os.remove(drafts_file_path)
                except PermissionError:
                    time.sleep(0.2)
                    try:
                        os.remove(drafts_file_path)
                    except PermissionError:
                        pass  # Let test database cleanup handle it
