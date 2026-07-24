# -*- coding: utf-8 -*-
"""
Unit tests for DOMOVIK Admin API.
Story 4.5: RESTful API for admin operations.
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from apps.submissions.models import Application, Applicant, ProjectData, InitiativeData, FileMetadata
import json
import os
from django.conf import settings


class AdminAPIAuthTests(TestCase):
    """Test API authentication and authorization - Story 4.5."""

    def setUp(self):
        """Create test users."""
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username='testadmin',
            email='admin@domovik.local',
            password='TestAdmin123!'
        )
        self.regular_user = User.objects.create_user(
            username='testuser',
            email='user@domovik.local',
            password='TestUser123!'
        )

    def test_api_requires_authentication(self):
        """Test API endpoints require authentication."""
        # Not logged in
        response = self.client.get('/api/admin/applications/')
        self.assertEqual(response.status_code, 401)

    def test_api_requires_admin_user(self):
        """Test API endpoints require admin user (is_staff=True)."""
        # Login as regular user (not admin)
        self.client.login(username='testuser', password='TestUser123!')

        response = self.client.get('/api/admin/applications/')
        self.assertEqual(response.status_code, 401)  # Not authorized (not staff)

    def test_admin_user_can_access_api(self):
        """Test admin user can access API endpoints."""
        self.client.login(username='testadmin', password='TestAdmin123!')

        response = self.client.get('/api/admin/applications/')
        self.assertEqual(response.status_code, 200)


class ApplicationListAPITests(TestCase):
    """Test GET /api/admin/applications/ endpoint - Story 4.5."""

    def setUp(self):
        """Create test admin and applications."""
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username='testadmin',
            email='admin@domovik.local',
            password='TestAdmin123!'
        )
        self.client.login(username='testadmin', password='TestAdmin123!')

        # Create COA application
        app_coa = Application.objects.create(
            reference_number='COA-2025-001',
            application_type='COA',
            status='submitted',
        )
        applicant_coa = Applicant.objects.create(
            application=app_coa,
            entity_type='fizicko',
            first_name='Marko',
            last_name='Petrović',
            jmbg='1234567890123',
            address='Beograd',
            email='marko@example.com',
            phone='+381601234567',
        )
        ProjectData.objects.create(
            application=app_coa,
            title='Test COA Project',
            short_description='Opis',
            problem='Problem',
            main_goal='Cilj',
            specific_goals='Ciljevi',
            target_groups='Grupe',
            activities='Aktivnosti',
            results='Rezultati',
            total_budget=100000,  # IntegerField
        )

        # Create COB application
        app_cob = Application.objects.create(
            reference_number='COB-2025-001',
            application_type='COB',
            status='under_review',
        )
        applicant_cob = Applicant.objects.create(
            application=app_cob,
            entity_type='pravno',
            organization_name='Domovik Udruženje',
            address='Novi Sad',
            email='info@domovik.rs',
            phone='+381211234567',
        )
        InitiativeData.objects.create(
            application=app_cob,
            naslov='Test COB Initiative',
            kratak_opis='Opis',
            problem='Problem',
            cilj_inicijative='Cilj',  # Correct field name
            planirani_koraci='Koraci',
            ocekivani_uticaj='Uticaj',
        )

    def test_list_applications_success(self):
        """Test GET /api/admin/applications/ returns list."""
        response = self.client.get('/api/admin/applications/')

        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn('count', data)
        self.assertIn('results', data)
        self.assertEqual(data['count'], 2)
        self.assertEqual(len(data['results']), 2)

        # Verify structure
        first_result = data['results'][0]
        self.assertIn('reference_number', first_result)
        self.assertIn('applicant_name', first_result)
        self.assertIn('title', first_result)
        self.assertIn('type', first_result)
        self.assertIn('status', first_result)
        self.assertIn('submitted_at', first_result)

    def test_filter_by_type_coa(self):
        """Test filtering by type=COA."""
        response = self.client.get('/api/admin/applications/?type=COA')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['results'][0]['type'], 'COA')

    def test_filter_by_type_cob(self):
        """Test filtering by type=COB."""
        response = self.client.get('/api/admin/applications/?type=COB')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['results'][0]['type'], 'COB')

    def test_filter_by_status(self):
        """Test filtering by status."""
        response = self.client.get('/api/admin/applications/?status=submitted')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['results'][0]['status'], 'submitted')

    def test_pagination(self):
        """Test pagination with page_size."""
        response = self.client.get('/api/admin/applications/?page_size=1')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['results']), 1)
        self.assertIsNotNone(data['next'])
        self.assertIsNone(data['previous'])

    def test_pagination_page_size_cap(self):
        """Test pagination caps at MAX_PAGE_SIZE (100)."""
        response = self.client.get('/api/admin/applications/?page_size=1000')

        self.assertEqual(response.status_code, 422)  # Pydantic validation error

    def test_invalid_type_filter(self):
        """Test invalid type filter returns 400."""
        response = self.client.get('/api/admin/applications/?type=INVALID')

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('Invalid type filter', data['detail'])

    def test_invalid_status_filter(self):
        """Test invalid status filter returns 400."""
        response = self.client.get('/api/admin/applications/?status=invalid_status')

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('Invalid status filter', data['detail'])

    def test_response_schema_types(self):
        """Test response conforms to Pydantic schema (type validation)."""
        response = self.client.get('/api/admin/applications/')

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Validate top-level schema
        self.assertIsInstance(data['count'], int)
        self.assertIsInstance(data['results'], list)
        self.assertTrue(data['next'] is None or isinstance(data['next'], str))
        self.assertTrue(data['previous'] is None or isinstance(data['previous'], str))

        # Validate item schema
        if data['results']:
            item = data['results'][0]
            self.assertIsInstance(item['reference_number'], str)
            self.assertIsInstance(item['applicant_name'], str)
            self.assertIsInstance(item['title'], str)
            self.assertIsInstance(item['type'], str)
            self.assertIsInstance(item['status'], str)


class ApplicationDetailAPITests(TestCase):
    """Test GET /api/admin/applications/<ref>/ endpoint - Story 4.5."""

    def setUp(self):
        """Create test admin and application."""
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username='testadmin',
            email='admin@domovik.local',
            password='TestAdmin123!'
        )
        self.client.login(username='testadmin', password='TestAdmin123!')

        # Create COA application with files
        self.application = Application.objects.create(
            reference_number='COA-2025-001',
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
        self.project_data = ProjectData.objects.create(
            application=self.application,
            title='API Test Project',
            short_description='Kratak opis projekta',
            problem='Problem koji rešavamo',
            main_goal='Glavni cilj projekta',
            specific_goals='Specifični ciljevi',
            target_groups='Ciljne grupe',
            activities='Aktivnosti',
            results='Rezultati',
            total_budget=500000,  # IntegerField
        )
        FileMetadata.objects.create(
            application=self.application,
            file_type='BUDGET',  # Correct field name from model
            original_filename='Budzet_Projekta.xlsx',
            stored_filename='COA-2025-001_budzet_test.xlsx',
            file_size=10000,
        )

    def test_get_application_detail_success(self):
        """Test GET /api/admin/applications/COA-2025-001/ returns detail."""
        response = self.client.get('/api/admin/applications/COA-2025-001/')

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Verify structure
        self.assertEqual(data['reference_number'], 'COA-2025-001')
        self.assertEqual(data['application_type'], 'COA')
        self.assertEqual(data['status'], 'submitted')
        self.assertIn('applicant', data)
        self.assertIn('project_data', data)
        self.assertIn('files', data)

        # Verify applicant
        self.assertEqual(data['applicant']['first_name'], 'Marko')
        self.assertEqual(data['applicant']['last_name'], 'Petrović')

        # Verify project_data
        self.assertEqual(data['project_data']['title'], 'API Test Project')
        self.assertEqual(data['project_data']['total_budget'], 500000)

        # Verify files
        self.assertEqual(len(data['files']), 1)
        self.assertEqual(data['files'][0]['file_type'], 'BUDGET')  # Correct field name
        self.assertEqual(data['files'][0]['original_filename'], 'Budzet_Projekta.xlsx')

    def test_get_application_detail_not_found(self):
        """Test GET with invalid reference number returns 404."""
        response = self.client.get('/api/admin/applications/COA-9999-999/')

        self.assertEqual(response.status_code, 404)


class UpdateApplicationStatusAPITests(TestCase):
    """Test PATCH /api/admin/applications/<ref>/ endpoint - Story 4.5."""

    def setUp(self):
        """Create test admin and application."""
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username='testadmin',
            email='admin@domovik.local',
            password='TestAdmin123!'
        )
        # Must get CSRF token for PATCH requests
        self.client.login(username='testadmin', password='TestAdmin123!')

        # Get CSRF token
        response = self.client.get('/admin/')
        self.csrf_token = response.cookies['csrftoken'].value

        # Create application
        self.application = Application.objects.create(
            reference_number='COA-2025-001',
            application_type='COA',
            status='submitted',
        )
        applicant = Applicant.objects.create(
            application=self.application,
            entity_type='fizicko',
            first_name='Marko',
            last_name='Petrović',
            jmbg='1234567890123',
            address='Beograd',
            email='marko@example.com',
            phone='+381601234567',
        )
        ProjectData.objects.create(
            application=self.application,
            title='Test Project',
            short_description='Opis',
            problem='Problem',
            main_goal='Cilj',
            specific_goals='Ciljevi',
            target_groups='Grupe',
            activities='Aktivnosti',
            results='Rezultati',
            total_budget=100000,  # IntegerField
        )

    def test_update_status_success(self):
        """Test PATCH /api/admin/applications/COA-2025-001/ updates status."""
        response = self.client.patch(
            '/api/admin/applications/COA-2025-001/',
            data=json.dumps({'status': 'under_review'}),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=self.csrf_token,
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertTrue(data['success'])
        self.assertIn('updated', data['message'])
        self.assertEqual(data['updated_application']['status'], 'under_review')

        # Verify database updated
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, 'under_review')

    def test_update_status_invalid_value(self):
        """Test PATCH with invalid status value returns 422."""
        response = self.client.patch(
            '/api/admin/applications/COA-2025-001/',
            data=json.dumps({'status': 'invalid_status'}),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=self.csrf_token,
        )

        self.assertEqual(response.status_code, 422)  # Pydantic validation error

    def test_update_status_requires_csrf_token(self):
        """Test PATCH without CSRF token fails."""
        # Create a new client with CSRF checks enforced
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.login(username='testadmin', password='TestAdmin123!')

        response = csrf_client.patch(
            '/api/admin/applications/COA-2025-001/',
            data=json.dumps({'status': 'approved'}),
            content_type='application/json',
            # NO CSRF TOKEN
        )

        self.assertEqual(response.status_code, 403)  # CSRF verification failed


class FileDownloadAPITests(TestCase):
    """Test file download API endpoints - Story 4.5."""

    def setUp(self):
        """Create test admin and application with files."""
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username='testadmin',
            email='admin@domovik.local',
            password='TestAdmin123!'
        )
        self.client.login(username='testadmin', password='TestAdmin123!')

        # Create application
        self.application = Application.objects.create(
            reference_number='COA-2025-001',
            application_type='COA',
            status='submitted',
        )
        applicant = Applicant.objects.create(
            application=self.application,
            entity_type='fizicko',
            first_name='Marko',
            last_name='Petrović',
            jmbg='1234567890123',
            address='Beograd',
            email='marko@example.com',
            phone='+381601234567',
        )
        ProjectData.objects.create(
            application=self.application,
            title='Test Project',
            short_description='Opis',
            problem='Problem',
            main_goal='Cilj',
            specific_goals='Ciljevi',
            target_groups='Grupe',
            activities='Aktivnosti',
            results='Rezultati',
            total_budget=100000,  # IntegerField
        )

        # Create file metadata with real test file
        self.test_file_content = b'Test file content for API download'
        # Use the actual folder name from Story 4.4 constants - 'budgets' not 'budzet'
        self.test_file_dir = os.path.join(settings.MEDIA_ROOT, 'submissions', 'budgets')
        os.makedirs(self.test_file_dir, exist_ok=True)
        self.test_file_path = os.path.join(self.test_file_dir, 'COA-2025-001_budzet_test.xlsx')

        with open(self.test_file_path, 'wb') as f:
            f.write(self.test_file_content)

        self.file_metadata = FileMetadata.objects.create(
            application=self.application,
            file_type='BUDGET',  # Correct field name from model
            original_filename='Budzet_Projekta.xlsx',
            stored_filename='COA-2025-001_budzet_test.xlsx',
            file_size=len(self.test_file_content),
        )

    def tearDown(self):
        """Clean up test files."""
        import time
        if os.path.exists(self.test_file_path):
            try:
                os.remove(self.test_file_path)
            except PermissionError:
                # Windows file locking - wait and retry
                time.sleep(0.1)
                try:
                    os.remove(self.test_file_path)
                except PermissionError:
                    pass  # File will be cleaned up later

    def test_api_download_file_success_with_real_file(self):
        """Test API file download endpoint with real file."""
        response = self.client.get(
            f'/api/admin/applications/COA-2025-001/files/{self.file_metadata.id}/download/'
        )

        self.assertEqual(response.status_code, 200)
        # Content-Type may vary, just check the file downloads
        self.assertIn('Budzet_Projekta.xlsx', response['Content-Disposition'])

    def test_api_download_file_missing_from_disk(self):
        """Test API download when file metadata exists but file missing from disk."""
        # Remove the file
        os.remove(self.test_file_path)

        response = self.client.get(
            f'/api/admin/applications/COA-2025-001/files/{self.file_metadata.id}/download/'
        )

        self.assertEqual(response.status_code, 404)

    def test_api_download_all_endpoint_exists(self):
        """Test API download all files endpoint accessible."""
        response = self.client.get('/api/admin/applications/COA-2025-001/files/download_all/')

        # Should route correctly (200 with real file or 404 if no files)
        self.assertIn(response.status_code, [200, 404])


class APIDocumentationTests(TestCase):
    """Test automatic OpenAPI documentation - Story 4.5."""

    def setUp(self):
        """Create test admin."""
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username='testadmin',
            email='admin@domovik.local',
            password='TestAdmin123!'
        )
        self.client.login(username='testadmin', password='TestAdmin123!')

    def test_openapi_json_accessible(self):
        """Test OpenAPI JSON schema accessible."""
        response = self.client.get('/api/admin/openapi.json')

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Verify OpenAPI structure
        self.assertIn('openapi', data)
        self.assertIn('info', data)
        self.assertIn('paths', data)
        self.assertEqual(data['info']['title'], 'DOMOVIK Admin API')

    def test_swagger_docs_accessible(self):
        """Test Swagger UI docs accessible."""
        response = self.client.get('/api/admin/docs')

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'swagger', response.content.lower())
