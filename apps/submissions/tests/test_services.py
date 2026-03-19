# -*- coding: utf-8 -*-
"""
Tests for Submission Services (Story 2.11)

Tests:
1. Reference number generation (sequential, year-based reset)
2. Thread-safe generation (no race conditions)
3. Submission processing (atomic transactions)
4. Error handling and rollback
"""

from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from django.conf import settings
from apps.submissions.models import (
    ReferenceNumberSequence,
    Application,
    Applicant,
    ProjectData,
    FileMetadata
)
from apps.submissions.services import ReferenceNumberService, process_submission
from unittest.mock import patch
from threading import Thread
import time
import unittest


class ReferenceNumberServiceTestCase(TestCase):
    """Test suite for ReferenceNumberService"""

    def setUp(self):
        """Set up test fixtures"""
        # Clear any existing sequences
        ReferenceNumberSequence.objects.all().delete()

    def test_generate_first_reference_number_coa(self):
        """Test generating the first COA reference number"""
        ref_num = ReferenceNumberService.generate_reference_number('COA')
        current_year = timezone.now().year
        expected = f"COA-{current_year}-001"
        self.assertEqual(ref_num, expected)

    def test_generate_first_reference_number_cob(self):
        """Test generating the first COB reference number"""
        ref_num = ReferenceNumberService.generate_reference_number('COB')
        current_year = timezone.now().year
        expected = f"COB-{current_year}-001"
        self.assertEqual(ref_num, expected)

    def test_generate_sequential_numbers(self):
        """Test generating 5 sequential numbers (001, 002, 003, 004, 005)"""
        current_year = timezone.now().year
        expected_numbers = [
            f"COA-{current_year}-001",
            f"COA-{current_year}-002",
            f"COA-{current_year}-003",
            f"COA-{current_year}-004",
            f"COA-{current_year}-005"
        ]

        generated_numbers = []
        for _ in range(5):
            ref_num = ReferenceNumberService.generate_reference_number('COA')
            generated_numbers.append(ref_num)

        self.assertEqual(generated_numbers, expected_numbers)

    def test_sequential_numbering_no_gaps(self):
        """Test that sequential numbering has no gaps"""
        # Generate 10 numbers
        numbers = []
        for _ in range(10):
            ref_num = ReferenceNumberService.generate_reference_number('COA')
            # Extract just the sequential part (NNN)
            seq_num = int(ref_num.split('-')[-1])
            numbers.append(seq_num)

        # Verify continuous sequence 1, 2, 3, ..., 10
        expected = list(range(1, 11))
        self.assertEqual(numbers, expected)

    def test_separate_sequences_for_coa_and_cob(self):
        """Test that COA and COB have separate sequences"""
        current_year = timezone.now().year

        # Generate COA numbers
        coa_1 = ReferenceNumberService.generate_reference_number('COA')
        coa_2 = ReferenceNumberService.generate_reference_number('COA')

        # Generate COB numbers
        cob_1 = ReferenceNumberService.generate_reference_number('COB')
        cob_2 = ReferenceNumberService.generate_reference_number('COB')

        # COA and COB should both start at 001
        self.assertEqual(coa_1, f"COA-{current_year}-001")
        self.assertEqual(coa_2, f"COA-{current_year}-002")
        self.assertEqual(cob_1, f"COB-{current_year}-001")
        self.assertEqual(cob_2, f"COB-{current_year}-002")

    @patch('django.utils.timezone.now')
    def test_year_based_reset(self, mock_now):
        """Test that sequence resets to 001 when year changes"""
        # Mock current year as 2025
        from datetime import datetime
        mock_now.return_value = datetime(2025, 12, 31, 23, 59, 59)

        # Generate number in 2025
        ref_2025 = ReferenceNumberService.generate_reference_number('COA')
        self.assertEqual(ref_2025, "COA-2025-001")

        # Mock year change to 2026
        mock_now.return_value = datetime(2026, 1, 1, 0, 0, 0)

        # Generate number in 2026 (should reset to 001)
        ref_2026 = ReferenceNumberService.generate_reference_number('COA')
        self.assertEqual(ref_2026, "COA-2026-001")

    def test_database_sequence_created(self):
        """Test that ReferenceNumberSequence record is created"""
        current_year = timezone.now().year

        # Verify no sequence exists initially
        self.assertFalse(
            ReferenceNumberSequence.objects.filter(
                year=current_year,
                application_type='COA'
            ).exists()
        )

        # Generate reference number
        ReferenceNumberService.generate_reference_number('COA')

        # Verify sequence record was created
        sequence = ReferenceNumberSequence.objects.get(
            year=current_year,
            application_type='COA'
        )
        self.assertEqual(sequence.last_number, 1)

    def test_format_three_digit_padding(self):
        """Test that numbers are formatted with 3-digit padding"""
        current_year = timezone.now().year

        # Generate first 9 numbers and verify padding
        for i in range(1, 10):
            ref = ReferenceNumberService.generate_reference_number('COA')
            expected = f"COA-{current_year}-{i:03d}"
            self.assertEqual(ref, expected)

        # Generate numbers 10-99 and verify padding
        for i in range(10, 100):
            ref = ReferenceNumberService.generate_reference_number('COA')
            expected = f"COA-{current_year}-{i:03d}"
            self.assertEqual(ref, expected)

        # Generate number 100 and verify it's still formatted properly
        ref_100 = ReferenceNumberService.generate_reference_number('COA')
        self.assertEqual(ref_100, f"COA-{current_year}-100")


class ReferenceNumberThreadSafetyTestCase(TransactionTestCase):
    """Test suite for thread-safety of reference number generation"""

    @unittest.skipUnless(
        settings.DATABASES['default']['ENGINE'] != 'django.db.backends.sqlite3',
        "SQLite doesn't support concurrent transactions properly - skip threading test"
    )
    def test_concurrent_generation_no_duplicates(self):
        """Test that concurrent generation doesn't create duplicate numbers"""
        # Clear any existing sequences
        ReferenceNumberSequence.objects.all().delete()

        # Storage for generated numbers
        generated_numbers = []

        def generate_number():
            """Thread worker function"""
            ref_num = ReferenceNumberService.generate_reference_number('COA')
            generated_numbers.append(ref_num)

        # Create 10 threads that generate numbers concurrently
        threads = []
        for _ in range(10):
            thread = Thread(target=generate_number)
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify: 10 unique numbers generated
        self.assertEqual(len(generated_numbers), 10)
        self.assertEqual(len(set(generated_numbers)), 10)  # All unique

        # Verify: Sequential numbers from 001 to 010
        numbers = [int(ref.split('-')[-1]) for ref in generated_numbers]
        numbers.sort()
        self.assertEqual(numbers, list(range(1, 11)))


class ProcessSubmissionTestCase(TestCase):
    """Test suite for process_submission function"""

    def setUp(self):
        """Set up test fixtures"""
        # Clear database
        Application.objects.all().delete()
        Applicant.objects.all().delete()
        ProjectData.objects.all().delete()
        FileMetadata.objects.all().delete()
        ReferenceNumberSequence.objects.all().delete()

    def test_successful_coa_submission(self):
        """Test successful COA submission with all data"""
        submission_data = {
            'application_type': 'COA',
            'applicant': {
                'entity_type': 'fizicko',
                'first_name': 'Marko',
                'last_name': 'Marković',
                'address': 'Kneza Miloša 10, Beograd',
                'email': 'marko@example.com',
                'phone': '+381611234567',
                'jmbg': 'ID1234567'  # Story 5.1: ID broj format (ID + 7 digits)
            },
            'project': {
                'title': 'Test Projekat',
                'short_description': 'Kratak opis projekta',
                'problem': 'Problem koji se rešava',
                'main_goal': 'Glavni cilj projekta',
                'specific_goals': 'Specifični ciljevi',
                'target_groups': 'Ciljne grupe',
                'activities': 'Aktivnosti',
                'results': 'Očekivani rezultati',
                'total_budget': 1000000
            },
            'files': [
                {
                    'file_type': 'BUDGET',
                    'original_filename': 'budzet.xlsx',
                    'stored_filename': 'stored_budzet_123.xlsx',
                    'file_size': 52341
                }
            ],
            'consent': {
                'privacy': True,
                'terms': True,
                'accuracy': True
            }
        }

        result = process_submission(submission_data)

        # Verify success
        self.assertTrue(result['success'])
        self.assertIn('reference_number', result)
        self.assertTrue(result['reference_number'].startswith('COA-'))

        # Verify Application created
        application = Application.objects.get(reference_number=result['reference_number'])
        self.assertEqual(application.application_type, 'COA')
        self.assertEqual(application.status, 'submitted')
        self.assertIsNotNone(application.submitted_at)

        # Verify Applicant created
        applicant = application.applicant
        self.assertEqual(applicant.first_name, 'Marko')
        self.assertEqual(applicant.last_name, 'Marković')
        self.assertEqual(applicant.email, 'marko@example.com')

        # Verify ProjectData created
        project = application.project_data
        self.assertEqual(project.title, 'Test Projekat')
        self.assertEqual(project.total_budget, 1000000)

        # Verify FileMetadata created
        files = application.files.all()
        self.assertEqual(files.count(), 1)
        self.assertEqual(files[0].file_type, 'BUDGET')

    def test_submission_with_multiple_files(self):
        """Test submission with multiple files (budget + biografije)"""
        submission_data = {
            'application_type': 'COA',
            'applicant': {
                'entity_type': 'pravno',
                'organization_name': 'Test Org',
                'address': 'Adresa 1',
                'email': 'org@example.com',
                'phone': '+381111234567',
                'maticni_broj': 'REG-123456'  # Story 5.1: Changed to registracioni broj format
            },
            'project': {
                'title': 'Projekat',
                'short_description': 'Opis',
                'problem': 'Problem',
                'main_goal': 'Cilj',
                'specific_goals': 'Spec ciljevi',
                'target_groups': 'Grupe',
                'activities': 'Aktivnosti',
                'results': 'Rezultati',
                'total_budget': 500000
            },
            'files': [
                {
                    'file_type': 'BUDGET',
                    'original_filename': 'budzet.xlsx',
                    'stored_filename': 'stored_1.xlsx',
                    'file_size': 10000
                },
                {
                    'file_type': 'BIOGRAPHY',
                    'original_filename': 'bio1.pdf',
                    'stored_filename': 'stored_2.pdf',
                    'file_size': 20000
                },
                {
                    'file_type': 'BIOGRAPHY',
                    'original_filename': 'bio2.pdf',
                    'stored_filename': 'stored_3.pdf',
                    'file_size': 15000
                }
            ]
        }

        result = process_submission(submission_data)

        # Verify success
        self.assertTrue(result['success'])

        # Verify 3 files created
        application = Application.objects.get(reference_number=result['reference_number'])
        self.assertEqual(application.files.count(), 3)

    def test_submission_atomic_transaction(self):
        """Test that failed submission rolls back all changes"""
        # Create submission with invalid data (missing required project fields)
        submission_data = {
            'application_type': 'COA',
            'applicant': {
                'entity_type': 'fizicko',
                'first_name': 'Test',
                'last_name': 'User',
                'address': 'Address',
                'email': 'test@example.com',
                'phone': '123456'
            },
            'project': {
                # Missing required fields - should cause error
                'title': None,  # Required field
                'total_budget': None  # Required field
            },
            'files': []
        }

        # Count records before submission
        app_count_before = Application.objects.count()
        applicant_count_before = Applicant.objects.count()

        result = process_submission(submission_data)

        # Verify failure
        self.assertFalse(result['success'])
        self.assertIn('error', result)

        # Verify no records were created (transaction rolled back)
        app_count_after = Application.objects.count()
        applicant_count_after = Applicant.objects.count()

        self.assertEqual(app_count_before, app_count_after)
        self.assertEqual(applicant_count_before, applicant_count_after)

    def test_utf8_serbian_characters(self):
        """Test that Serbian characters (č, ć, š, đ, ž) are stored correctly"""
        submission_data = {
            'application_type': 'COA',
            'applicant': {
                'entity_type': 'fizicko',
                'first_name': 'Đorđe',
                'last_name': 'Kovačević',
                'address': 'Kralja Petra 5, Niš',
                'email': 'djordje@example.com',
                'phone': '+381651234567',
                'jmbg': 'ID6543210'  # Story 5.1: ID broj format (ID + 7 digits)
            },
            'project': {
                'title': 'Побољшање инфраструктуре',
                'short_description': 'Краћи опис пројекта',
                'problem': 'Проблем који решавамо',
                'main_goal': 'Главни циљ',
                'specific_goals': 'Специфични циљеви',
                'target_groups': 'Циљне групе',
                'activities': 'Активности',
                'results': 'Резултати',
                'total_budget': 750000
            },
            'files': []
        }

        result = process_submission(submission_data)

        # Verify success
        self.assertTrue(result['success'])

        # Retrieve and verify Serbian characters preserved
        application = Application.objects.get(reference_number=result['reference_number'])
        self.assertEqual(application.applicant.first_name, 'Đorđe')
        self.assertEqual(application.applicant.last_name, 'Kovačević')
        self.assertEqual(application.project_data.title, 'Побољшање инфраструктуре')
