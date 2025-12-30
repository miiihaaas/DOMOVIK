# -*- coding: utf-8 -*-
"""
Integration tests for admin document download - Story 4.4.

Tests complete workflows:
- Downloading multiple files individually
- Creating and extracting valid ZIP archives
- Complete admin workflow from login to download
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.conf import settings
from apps.submissions.models import Application, Applicant, ProjectData, FileMetadata
import os
import zipfile
import time
from io import BytesIO


class AdminDownloadIntegrationTests(TestCase):
    """Integration tests for admin document download - Story 4.4."""

    def setUp(self):
        """Create test admin and application with multiple files."""
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username='testadmin',
            email='testadmin@domovik.local',
            password='TestAdmin123!'
        )

        # Create COA application
        self.application = Application.objects.create(
            reference_number='COA-2025-010',
            application_type='COA',
            status='submitted',
        )

        self.applicant = Applicant.objects.create(
            application=self.application,
            entity_type='fizicko',
            first_name='Marko',
            last_name='Petrović',
            jmbg='1234567890123',
            address='Beograd',
            email='marko@example.com',
            phone='+381601234567',
        )

        self.application.applicant = self.applicant
        self.application.save()

        ProjectData.objects.create(
            application=self.application,
            title='Integration Test Project',
            short_description='Test',
            problem='Test',
            main_goal='Test',
            specific_goals='Test',
            target_groups='Test',
            activities='Test',
            results='Test',
            total_budget=500000,
        )

        # Create multiple test files
        self.test_files = []

        # Budget file
        budget_path = os.path.join(
            settings.MEDIA_ROOT, 'submissions', 'budgets',
            'COA-2025-010_budzet_test1.xlsx'
        )
        os.makedirs(os.path.dirname(budget_path), exist_ok=True)
        with open(budget_path, 'wb') as f:
            f.write(b'Budget file content')
        self.test_files.append(budget_path)

        FileMetadata.objects.create(
            application=self.application,
            file_type='BUDZET',
            original_filename='Budzet_Projekta.xlsx',
            stored_filename='COA-2025-010_budzet_test1.xlsx',
            file_size=2000,
        )

        # Biography file
        bio_path = os.path.join(
            settings.MEDIA_ROOT, 'submissions', 'biographies',
            'COA-2025-010_biografija_test2.pdf'
        )
        os.makedirs(os.path.dirname(bio_path), exist_ok=True)
        with open(bio_path, 'wb') as f:
            f.write(b'Biography PDF content')
        self.test_files.append(bio_path)

        FileMetadata.objects.create(
            application=self.application,
            file_type='BIOGRAFIJA',
            original_filename='Biografija_Tim_Lider.pdf',
            stored_filename='COA-2025-010_biografija_test2.pdf',
            file_size=5000,
        )

    def tearDown(self):
        """Clean up test files."""
        # Small delay to allow Windows to release file locks
        time.sleep(0.1)

        for file_path in self.test_files:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except PermissionError:
                    # File still locked, wait and retry
                    time.sleep(0.2)
                    try:
                        os.remove(file_path)
                    except PermissionError:
                        pass  # Let test database cleanup handle it

    def test_download_multiple_files_individually(self):
        """Test admin can download multiple files individually."""
        self.client.login(username='testadmin', password='TestAdmin123!')

        files = FileMetadata.objects.filter(application=self.application)

        for file_metadata in files:
            url = reverse('submissions:admin_download_file', args=[self.application.id, file_metadata.id])
            response = self.client.get(url)

            self.assertEqual(response.status_code, 200)
            self.assertIn('attachment', response['Content-Disposition'])
            self.assertIn(file_metadata.original_filename, response['Content-Disposition'])

    def test_download_all_creates_valid_zip(self):
        """Test download all creates valid ZIP with all files."""
        self.client.login(username='testadmin', password='TestAdmin123!')

        url = reverse('submissions:admin_download_all', args=[self.application.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/zip')

        # Verify ZIP contents
        zip_content = BytesIO(response.content)
        with zipfile.ZipFile(zip_content, 'r') as zip_file:
            # Verify both files in ZIP
            namelist = zip_file.namelist()
            self.assertEqual(len(namelist), 2)
            self.assertIn('Budzet_Projekta.xlsx', namelist)
            self.assertIn('Biografija_Tim_Lider.pdf', namelist)

            # Verify file contents
            self.assertEqual(zip_file.read('Budzet_Projekta.xlsx'), b'Budget file content')
            self.assertEqual(zip_file.read('Biografija_Tim_Lider.pdf'), b'Biography PDF content')

    def test_admin_workflow_view_and_download(self):
        """Test complete admin workflow: login → view detail → download file."""
        # Login
        self.client.login(username='testadmin', password='TestAdmin123!')

        # Navigate to list view
        list_response = self.client.get('/admin/submissions/application/')
        self.assertEqual(list_response.status_code, 200)

        # Navigate to detail view
        detail_response = self.client.get(f'/admin/submissions/application/{self.application.id}/change/')
        self.assertEqual(detail_response.status_code, 200)

        # Verify download links present
        self.assertContains(detail_response, '⬇️ Download')
        self.assertContains(detail_response, 'Download All Documents')

        # Download individual file
        file_metadata = FileMetadata.objects.filter(application=self.application).first()
        download_url = reverse('submissions:admin_download_file', args=[self.application.id, file_metadata.id])
        download_response = self.client.get(download_url)

        self.assertEqual(download_response.status_code, 200)
        self.assertIn(file_metadata.original_filename, download_response['Content-Disposition'])

        # Download all files
        download_all_url = reverse('submissions:admin_download_all', args=[self.application.id])
        download_all_response = self.client.get(download_all_url)

        self.assertEqual(download_all_response.status_code, 200)
        self.assertIn('COA-2025-010_documents.zip', download_all_response['Content-Disposition'])
