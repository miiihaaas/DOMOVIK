# -*- coding: utf-8 -*-
"""
Integration Tests for Complete Submission Flow
Story 2.11: Reference Number Generation & Submission Processing

Test Scenarios:
1. Happy path: Complete submission with all data
2. Error handling: Missing data, invalid data
3. Rollback: Verify atomic transactions on failure
4. File linking: Ensure uploaded files are linked to application
5. Reference number generation: Verify unique sequential numbers
"""

import json
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.sessions.middleware import SessionMiddleware
from django.test.client import RequestFactory
from apps.submissions.models import (
    Application,
    Applicant,
    ProjectData,
    FileMetadata,
    UploadedFile,
    ReferenceNumberSequence
)
from apps.submissions.services import process_submission, ReferenceNumberService


class SubmissionIntegrationTest(TestCase):
    """Integration tests for complete submission flow"""

    def setUp(self):
        """Set up test client and session"""
        self.client = Client()
        self.factory = RequestFactory()

        # Create session for file upload tests
        session = self.client.session
        session.save()
        self.session_key = session.session_key

        # Submit URL
        self.submit_url = reverse('submissions:submit_application')

    def test_happy_path_complete_submission(self):
        """
        Test 1: Happy path - Complete COA submission with all required data

        Verifies:
        - Reference number is generated (COA-2025-001 format)
        - Application record is created
        - Applicant record is created and linked
        - ProjectData record is created and linked
        - Response includes reference number
        """
        # Prepare complete submission data
        submission_data = {
            'application_type': 'COA',
            'applicant': {
                'entity_type': 'fizicko',
                'first_name': 'Marko',
                'last_name': 'Marković',
                'jmbg': '0101990123456',
                'address': 'Kneza Miloša 10, Beograd',
                'email': 'marko@example.com',
                'phone': '+381111234567'
            },
            'project': {
                'title': 'Test Project',
                'short_description': 'Short description of the test project',
                'problem': 'Problem statement goes here with enough detail',
                'main_goal': 'Main objective of the project',
                'specific_goals': 'Specific objectives listed here',
                'target_groups': 'Target beneficiaries of the project',
                'activities': 'Planned activities for the project',
                'results': 'Expected outcomes and results',
                'total_budget': 500000
            },
            'consent': {
                'privacy': True,
                'terms': True,
                'accuracy': True
            }
        }

        # Submit via API
        response = self.client.post(
            self.submit_url,
            data=json.dumps(submission_data),
            content_type='application/json',
            HTTP_X_CSRFTOKEN='test-csrf-token'
        )

        # Assert HTTP 200 OK
        self.assertEqual(response.status_code, 200)

        # Parse JSON response
        response_data = response.json()

        # Assert success
        self.assertTrue(response_data['success'])
        self.assertIn('reference_number', response_data)

        # Verify reference number format: COA-YYYY-NNN
        reference_number = response_data['reference_number']
        self.assertRegex(reference_number, r'^COA-\d{4}-\d{3}$')

        # Verify Application was created
        application = Application.objects.get(reference_number=reference_number)
        self.assertEqual(application.application_type, 'COA')
        self.assertEqual(application.status, 'submitted')
        self.assertIsNotNone(application.submitted_at)

        # Verify Applicant was created and linked
        applicant = Applicant.objects.get(application=application)
        self.assertEqual(applicant.entity_type, 'fizicko')
        self.assertEqual(applicant.first_name, 'Marko')
        self.assertEqual(applicant.last_name, 'Marković')
        self.assertEqual(applicant.email, 'marko@example.com')

        # Verify ProjectData was created and linked
        project = ProjectData.objects.get(application=application)
        self.assertEqual(project.title, 'Test Project')
        self.assertEqual(project.total_budget, 500000)

        print(f"[PASS] Test 1: Happy path submission successful with reference number {reference_number}")

    def test_error_handling_missing_applicant_data(self):
        """
        Test 2: Error handling - Missing applicant data

        Verifies:
        - API returns error when applicant data is missing
        - No database records are created (rollback)
        - Error message is user-friendly (Serbian)
        """
        # Prepare incomplete submission data (missing applicant)
        submission_data = {
            'application_type': 'COA',
            'project': {
                'title': 'Test Project',
                'short_description': 'Description',
                'problem': 'Problem',
                'main_goal': 'Goal',
                'specific_goals': 'Goals',
                'target_groups': 'Groups',
                'activities': 'Activities',
                'results': 'Results',
                'total_budget': 500000
            }
        }

        # Submit via API
        response = self.client.post(
            self.submit_url,
            data=json.dumps(submission_data),
            content_type='application/json',
            HTTP_X_CSRFTOKEN='test-csrf-token'
        )

        # Assert HTTP 400 Bad Request
        self.assertEqual(response.status_code, 400)

        # Parse JSON response
        response_data = response.json()

        # Assert failure
        self.assertFalse(response_data['success'])
        self.assertIn('error', response_data)

        # Verify error message is in Serbian
        self.assertIn('podnosiocu', response_data['error'].lower())

        # Verify NO database records were created
        self.assertEqual(Application.objects.count(), 0)
        self.assertEqual(Applicant.objects.count(), 0)
        self.assertEqual(ProjectData.objects.count(), 0)

        print("[PASS] Test 2: Error handling for missing applicant data works correctly")

    def test_atomic_rollback_on_failure(self):
        """
        Test 3: Atomic rollback - Verify transaction rollback on error

        Verifies:
        - If any step fails, entire transaction is rolled back
        - No partial data is saved to database
        - Reference number sequence is not incremented on failure
        """
        # Get initial sequence number (should be 0 or not exist)
        initial_sequence_count = ReferenceNumberSequence.objects.count()

        # Prepare submission data with invalid budget (will cause error)
        submission_data = {
            'application_type': 'COA',
            'applicant': {
                'entity_type': 'fizicko',
                'first_name': 'Ana',
                'last_name': 'Anić',
                'address': 'Address',
                'email': 'ana@example.com',
                'phone': '+381111234567'
            },
            'project': {
                'title': 'Test Project',
                'short_description': 'Description',
                'problem': 'Problem',
                'main_goal': 'Goal',
                'specific_goals': 'Goals',
                'target_groups': 'Groups',
                'activities': 'Activities',
                'results': 'Results',
                'total_budget': 'INVALID_BUDGET'  # This will cause TypeError
            }
        }

        # Submit via service directly (to test transaction rollback)
        result = process_submission(submission_data)

        # Assert failure
        self.assertFalse(result['success'])
        self.assertIn('error', result)

        # Verify NO database records were created (full rollback)
        self.assertEqual(Application.objects.count(), 0)
        self.assertEqual(Applicant.objects.count(), 0)
        self.assertEqual(ProjectData.objects.count(), 0)

        # Verify reference number sequence was NOT incremented
        # Note: SQLite doesn't support true row locking, but we can verify count
        final_sequence_count = ReferenceNumberSequence.objects.count()

        # If sequence was created during failed transaction, it should be rolled back
        # So count should remain the same
        self.assertEqual(final_sequence_count, initial_sequence_count)

        print("[PASS] Test 3: Atomic rollback prevents partial data on failure")

    def test_file_linking_after_submission(self):
        """
        Test 4: File linking - Verify uploaded files are linked to application

        Verifies:
        - Files uploaded before submission are linked to application
        - FileMetadata records are created
        - File ownership is transferred from session to application
        """
        # Create uploaded files in session (simulate file upload)
        file1 = UploadedFile.objects.create(
            original_filename='budget.xlsx',
            stored_filename='unique_budget_123.xlsx',
            file_path='uploads/drafts/unique_budget_123.xlsx',
            file_size=50000,
            file_type='xlsx',
            mime_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            category='BUDGET',
            uploaded_by_session=self.session_key,
            application=None  # Draft file
        )

        file2 = UploadedFile.objects.create(
            original_filename='biography.pdf',
            stored_filename='unique_bio_456.pdf',
            file_path='uploads/drafts/unique_bio_456.pdf',
            file_size=100000,
            file_type='pdf',
            mime_type='application/pdf',
            category='BIOGRAPHY',
            uploaded_by_session=self.session_key,
            application=None  # Draft file
        )

        # Prepare submission data
        submission_data = {
            'application_type': 'COA',
            'applicant': {
                'entity_type': 'pravno',
                'organization_name': 'Test Organization',
                'maticni_broj': '12345678',
                'address': 'Terazije 1, Beograd',
                'email': 'org@example.com',
                'phone': '+381119876543'
            },
            'project': {
                'title': 'Organization Project',
                'short_description': 'Project description',
                'problem': 'Problem statement',
                'main_goal': 'Main goal',
                'specific_goals': 'Specific goals',
                'target_groups': 'Target groups',
                'activities': 'Activities',
                'results': 'Results',
                'total_budget': 1000000
            }
        }

        # Submit via API (with session)
        response = self.client.post(
            self.submit_url,
            data=json.dumps(submission_data),
            content_type='application/json',
            HTTP_X_CSRFTOKEN='test-csrf-token'
        )

        # Assert success
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertTrue(response_data['success'])

        # Get created application
        reference_number = response_data['reference_number']
        application = Application.objects.get(reference_number=reference_number)

        # Verify files are linked to application
        file1.refresh_from_db()
        file2.refresh_from_db()

        self.assertEqual(file1.application, application)
        self.assertEqual(file2.application, application)

        # Verify FileMetadata records were created
        file_metadata_records = FileMetadata.objects.filter(application=application)
        self.assertEqual(file_metadata_records.count(), 2)

        # Verify metadata content
        budget_metadata = file_metadata_records.get(file_type='BUDGET')
        self.assertEqual(budget_metadata.original_filename, 'budget.xlsx')
        self.assertEqual(budget_metadata.file_size, 50000)

        print(f"[PASS] Test 4: Files linked to application {reference_number}")

    def test_reference_number_sequential_generation(self):
        """
        Test 5: Reference number generation - Verify sequential numbering

        Verifies:
        - Reference numbers are sequential (001, 002, 003...)
        - No gaps in sequence
        - Format is correct (COA-YYYY-NNN)
        """
        # Create 3 submissions and verify sequential numbering
        reference_numbers = []

        for i in range(3):
            submission_data = {
                'application_type': 'COA',
                'applicant': {
                    'entity_type': 'fizicko',
                    'first_name': f'User{i}',
                    'last_name': f'Lastname{i}',
                    'address': 'Address',
                    'email': f'user{i}@example.com',
                    'phone': '+381111111111'
                },
                'project': {
                    'title': f'Project {i}',
                    'short_description': 'Description',
                    'problem': 'Problem',
                    'main_goal': 'Goal',
                    'specific_goals': 'Goals',
                    'target_groups': 'Groups',
                    'activities': 'Activities',
                    'results': 'Results',
                    'total_budget': 100000
                }
            }

            # Use service directly for speed
            result = process_submission(submission_data)
            self.assertTrue(result['success'])
            reference_numbers.append(result['reference_number'])

        # Verify sequential numbering
        self.assertEqual(len(reference_numbers), 3)

        # Extract sequence numbers from reference numbers
        # Format: COA-YYYY-NNN
        sequence_numbers = []
        for ref_num in reference_numbers:
            parts = ref_num.split('-')
            sequence_numbers.append(int(parts[2]))

        # Verify sequential: 001, 002, 003
        self.assertEqual(sequence_numbers, [1, 2, 3])

        print(f"[PASS] Test 5: Sequential reference numbers generated: {reference_numbers}")

    def test_missing_project_data_for_coa(self):
        """
        Test 6: Validation - COA requires project data

        Verifies:
        - API rejects COA submission without project data
        - Error message is clear and in Serbian
        """
        submission_data = {
            'application_type': 'COA',
            'applicant': {
                'entity_type': 'fizicko',
                'first_name': 'Test',
                'last_name': 'User',
                'address': 'Address',
                'email': 'test@example.com',
                'phone': '+381111111111'
            }
            # Missing 'project' data
        }

        response = self.client.post(
            self.submit_url,
            data=json.dumps(submission_data),
            content_type='application/json',
            HTTP_X_CSRFTOKEN='test-csrf-token'
        )

        self.assertEqual(response.status_code, 400)
        response_data = response.json()

        self.assertFalse(response_data['success'])
        self.assertIn('projektu', response_data['error'].lower())

        # Verify no records created
        self.assertEqual(Application.objects.count(), 0)

        print("[PASS] Test 6: COA validation requires project data")


class ReferenceNumberServiceTest(TestCase):
    """Unit tests for ReferenceNumberService"""

    def test_reference_number_format(self):
        """Test reference number format: COA-YYYY-NNN"""
        ref_num = ReferenceNumberService.generate_reference_number('COA')

        # Check format
        self.assertRegex(ref_num, r'^COA-\d{4}-\d{3}$')

        # Check year is current year
        import datetime
        current_year = datetime.datetime.now().year
        self.assertIn(str(current_year), ref_num)

        print(f"[PASS] Reference number format test: {ref_num}")

    def test_cob_reference_number_format(self):
        """Test COB reference number format: COB-YYYY-NNN"""
        ref_num = ReferenceNumberService.generate_reference_number('COB')

        # Check format
        self.assertRegex(ref_num, r'^COB-\d{4}-\d{3}$')
        self.assertTrue(ref_num.startswith('COB-'))

        print(f"[PASS] COB reference number format test: {ref_num}")

    def test_sequential_numbering(self):
        """Test sequential numbering without gaps"""
        ref1 = ReferenceNumberService.generate_reference_number('COA')
        ref2 = ReferenceNumberService.generate_reference_number('COA')
        ref3 = ReferenceNumberService.generate_reference_number('COA')

        # Extract sequence numbers
        seq1 = int(ref1.split('-')[2])
        seq2 = int(ref2.split('-')[2])
        seq3 = int(ref3.split('-')[2])

        # Verify sequential: N, N+1, N+2
        self.assertEqual(seq2, seq1 + 1)
        self.assertEqual(seq3, seq2 + 1)

        print(f"[PASS] Sequential numbering test: {ref1}, {ref2}, {ref3}")
