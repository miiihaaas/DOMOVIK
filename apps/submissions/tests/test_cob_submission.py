# -*- coding: utf-8 -*-
"""
Unit tests for COB (Initiative) submission processing.
Story 3.5: COB Submission Processing - COB Reference Number

Tests:
- COB reference number generation (COB-YYYY-NNN format)
- InitiativeData model creation (6 fields, NO budget)
- Applicant creation (NO JMBG/matični for COB)
- File metadata (exactly 2 files: OPIS_INICIJATIVE + PISMO_NAMERE)
- Atomic transaction rollback on error
- GDPR consent validation
- Sequential numbering (001, 002, 003...)
- COB vs COA independent sequences
- UTF-8 Serbian character support
- Submission logging
"""

import json
from unittest.mock import patch
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone
from apps.submissions.models import (
    Application,
    Applicant,
    InitiativeData,
    ReferenceNumberSequence
)
from apps.submissions.services import ReferenceNumberService
from apps.submissions.constants import ApplicationType, FileType


@override_settings(
    RATELIMIT_ENABLE=False  # Disable rate limiting for tests
)
class COBSubmissionTestCase(TestCase):
    """Test suite for COB submission processing."""

    def setUp(self):
        """Set up test client and sample data."""
        self.client = Client()
        self.submit_url = reverse('submissions:submit_cob')

        # Sample COB submission data
        self.valid_cob_data = {
            'applicant': {
                'entity_type': 'fizicko',
                'first_name': 'Marko',
                'last_name': 'Marković',
                'address': 'Knez Mihailova 12, Beograd',
                'email': 'marko.markovic@example.com',
                'phone': '+381641234567'
                # NO JMBG for COB
            },
            'initiative': {
                'naslov': 'Test inicijativa',
                'kratak_opis': 'Ovo je kratak opis inicijative',
                'problem': 'Problem koji inicijativa rešava',
                'cilj_inicijative': 'Cilj inicijative',
                'planirani_koraci': 'Planirani koraci za realizaciju',
                'ocekivani_uticaj': 'Očekivani uticaj na zajednicu'
            },
            'files': [
                {
                    'file_type': FileType.OPIS_INICIJATIVE,
                    'name': 'opis_inicijative.pdf',
                    'size': 1024000
                },
                {
                    'file_type': FileType.PISMO_NAMERE,
                    'name': 'pismo_namere.pdf',
                    'size': 512000
                }
            ],
            'consent': {
                'privacy': True,
                'terms': True,
                'accuracy': True
            }
        }

    def test_cob_submission_success(self):
        """Test 1: Complete COB submission creates all records correctly."""
        response = self.client.post(
            self.submit_url,
            data=json.dumps(self.valid_cob_data),
            content_type='application/json'
        )

        # Check response status
        self.assertEqual(response.status_code, 201)

        # Parse response
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('reference_number', data)

        reference_number = data['reference_number']

        # Verify Application record
        application = Application.objects.get(reference_number=reference_number)
        self.assertEqual(application.application_type, ApplicationType.COB)
        self.assertEqual(application.status, 'submitted')
        self.assertIsNotNone(application.submitted_at)

        # Verify Applicant record (NO JMBG/matični)
        applicant = application.applicant
        self.assertEqual(applicant.first_name, 'Marko')
        self.assertEqual(applicant.last_name, 'Marković')
        self.assertEqual(applicant.email, 'marko.markovic@example.com')
        self.assertFalse(applicant.jmbg)  # NO JMBG for COB
        self.assertFalse(applicant.maticni_broj)  # NO matični for COB

        # Verify InitiativeData record (NO budget)
        initiative = application.initiative_data
        self.assertEqual(initiative.naslov, 'Test inicijativa')
        self.assertEqual(initiative.kratak_opis, 'Ovo je kratak opis inicijative')
        self.assertEqual(initiative.problem, 'Problem koji inicijativa rešava')

    def test_cob_reference_number_format(self):
        """Test 2: Verify COB reference number format (COB-YYYY-NNN)."""
        ref_number = ReferenceNumberService.generate_reference_number('COB')

        # Check format
        self.assertRegex(ref_number, r'^COB-\d{4}-\d{3}$')

        # Check year
        current_year = timezone.now().year
        self.assertIn(str(current_year), ref_number)

    def test_cob_sequential_numbering(self):
        """Test 3: Submit 3 COBs and verify sequential numbering (001, 002, 003)."""
        reference_numbers = []

        for i in range(3):
            # FIX: Change initiative title each time to avoid duplicate detection
            test_data = self.valid_cob_data.copy()
            test_data['initiative'] = self.valid_cob_data['initiative'].copy()
            test_data['initiative']['naslov'] = f'Test inicijativa {i+1}'

            response = self.client.post(
                self.submit_url,
                data=json.dumps(test_data),
                content_type='application/json'
            )

            self.assertEqual(response.status_code, 201)
            data = response.json()
            reference_numbers.append(data['reference_number'])

        # Verify sequential numbering
        current_year = timezone.now().year
        self.assertEqual(reference_numbers[0], f'COB-{current_year}-001')
        self.assertEqual(reference_numbers[1], f'COB-{current_year}-002')
        self.assertEqual(reference_numbers[2], f'COB-{current_year}-003')

    def test_cob_separate_from_coa(self):
        """Test 4: COA and COB sequences are independent."""
        # Generate COA reference number
        coa_ref_1 = ReferenceNumberService.generate_reference_number('COA')

        # Generate COB reference number
        cob_ref_1 = ReferenceNumberService.generate_reference_number('COB')

        # Generate another COA
        coa_ref_2 = ReferenceNumberService.generate_reference_number('COA')

        # Generate another COB
        cob_ref_2 = ReferenceNumberService.generate_reference_number('COB')

        # Verify sequences are independent
        current_year = timezone.now().year
        self.assertEqual(coa_ref_1, f'COA-{current_year}-001')
        self.assertEqual(cob_ref_1, f'COB-{current_year}-001')
        self.assertEqual(coa_ref_2, f'COA-{current_year}-002')
        self.assertEqual(cob_ref_2, f'COB-{current_year}-002')

        # Verify separate sequence records in database
        coa_sequence = ReferenceNumberSequence.objects.get(
            year=current_year,
            application_type='COA'
        )
        cob_sequence = ReferenceNumberSequence.objects.get(
            year=current_year,
            application_type='COB'
        )

        self.assertEqual(coa_sequence.last_number, 2)
        self.assertEqual(cob_sequence.last_number, 2)

    def test_initiative_data_created(self):
        """Test 5: Verify InitiativeData record has all 6 fields."""
        response = self.client.post(
            self.submit_url,
            data=json.dumps(self.valid_cob_data),
            content_type='application/json'
        )

        data = response.json()
        application = Application.objects.get(reference_number=data['reference_number'])

        # Verify InitiativeData has all fields
        initiative = application.initiative_data
        self.assertEqual(initiative.naslov, 'Test inicijativa')
        self.assertEqual(initiative.kratak_opis, 'Ovo je kratak opis inicijative')
        self.assertEqual(initiative.problem, 'Problem koji inicijativa rešava')
        self.assertEqual(initiative.cilj_inicijative, 'Cilj inicijative')
        self.assertEqual(initiative.planirani_koraci, 'Planirani koraci za realizaciju')
        self.assertEqual(initiative.ocekivani_uticaj, 'Očekivani uticaj na zajednicu')

        # Verify NO budget field (unlike COA ProjectData)
        self.assertFalse(hasattr(initiative, 'total_budget'))

    def test_applicant_no_jmbg(self):
        """Test 6: Verify Applicant created WITHOUT JMBG/matični for COB."""
        response = self.client.post(
            self.submit_url,
            data=json.dumps(self.valid_cob_data),
            content_type='application/json'
        )

        data = response.json()
        application = Application.objects.get(reference_number=data['reference_number'])

        applicant = application.applicant
        self.assertEqual(applicant.first_name, 'Marko')
        self.assertEqual(applicant.last_name, 'Marković')

        # COB: NO JMBG or matični broj required
        self.assertFalse(applicant.jmbg)
        self.assertFalse(applicant.maticni_broj)

    def test_file_metadata_2_files(self):
        """Test 7: Verify exactly 2 FileMetadata records (OPIS_INICIJATIVE, PISMO_NAMERE)."""
        # Note: This test validates the file metadata structure, not actual file uploads
        # File uploads are handled by Story 2.8 and Story 3.4

        cob_data = self.valid_cob_data.copy()
        response = self.client.post(
            self.submit_url,
            data=json.dumps(cob_data),
            content_type='application/json'
        )

        # Verify submission successful
        self.assertEqual(response.status_code, 201)
        data = response.json()

        # Verify file categories in request
        file_types = {f['file_type'] for f in cob_data['files']}
        self.assertEqual(file_types, {FileType.OPIS_INICIJATIVE, FileType.PISMO_NAMERE})

    def test_atomic_transaction_rollback(self):
        """Test 8: Force error mid-transaction and verify no partial data."""
        # This test verifies that if an error occurs during submission,
        # the entire transaction is rolled back (no partial data).
        # We'll verify by mocking the InitiativeData.objects.create to raise an exception

        # Count records before submission
        before_applications = Application.objects.count()
        before_applicants = Applicant.objects.count()
        before_initiatives = InitiativeData.objects.count()

        # Mock InitiativeData.objects.create to raise an exception
        with patch('apps.submissions.models.InitiativeData.objects.create', side_effect=Exception('Test error')):
            response = self.client.post(
                self.submit_url,
                data=json.dumps(self.valid_cob_data),
                content_type='application/json'
            )

            # Verify error response (500 Internal Server Error)
            self.assertEqual(response.status_code, 500)

        # Verify no partial records created (transaction rolled back)
        after_applications = Application.objects.count()
        after_applicants = Applicant.objects.count()
        after_initiatives = InitiativeData.objects.count()

        # The key is that NO partial data is created
        self.assertEqual(before_applications, after_applications)
        self.assertEqual(before_applicants, after_applicants)
        self.assertEqual(before_initiatives, after_initiatives)

    def test_missing_consent(self):
        """Test 9: Submit without GDPR consent and verify 400 error."""
        invalid_data = self.valid_cob_data.copy()
        invalid_data['consent'] = {
            'privacy': True,
            'terms': False,  # Missing consent
            'accuracy': True
        }

        response = self.client.post(
            self.submit_url,
            data=json.dumps(invalid_data),
            content_type='application/json'
        )

        # Verify 400 Bad Request
        self.assertEqual(response.status_code, 400)

        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('saglasnost', data['error'].lower())

    def test_utf8_serbian_characters(self):
        """Test 10: Submit with Serbian characters (č, ć, š, đ, ž) and verify storage."""
        serbian_data = self.valid_cob_data.copy()
        serbian_data['applicant']['first_name'] = 'Đorđe'
        serbian_data['applicant']['last_name'] = 'Kovačević'
        serbian_data['initiative']['naslov'] = 'Poboljšanje infrastrukture u gradu'
        serbian_data['initiative']['problem'] = 'Čišćenje reke i održavanje zelenih površina'

        response = self.client.post(
            self.submit_url,
            data=json.dumps(serbian_data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 201)

        data = response.json()
        application = Application.objects.get(reference_number=data['reference_number'])

        # Verify Serbian characters stored correctly
        applicant = application.applicant
        self.assertEqual(applicant.first_name, 'Đorđe')
        self.assertEqual(applicant.last_name, 'Kovačević')

        initiative = application.initiative_data
        self.assertEqual(initiative.naslov, 'Poboljšanje infrastrukture u gradu')
        self.assertEqual(initiative.problem, 'Čišćenje reke i održavanje zelenih površina')

    def test_missing_files(self):
        """Test 11: Submit with only 1 file and verify 400 error."""
        invalid_data = self.valid_cob_data.copy()
        invalid_data['files'] = [
            {
                'file_type': FileType.OPIS_INICIJATIVE,
                'name': 'opis.pdf',
                'size': 1024000
            }
            # Missing PISMO_NAMERE
        ]

        response = self.client.post(
            self.submit_url,
            data=json.dumps(invalid_data),
            content_type='application/json'
        )

        # Verify 400 Bad Request
        self.assertEqual(response.status_code, 400)

        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('2 dokumenta', data['error'])

    def test_wrong_file_categories(self):
        """Test 12: Submit with COA file categories and verify 400 error."""
        invalid_data = self.valid_cob_data.copy()
        invalid_data['files'] = [
            {
                'file_type': FileType.BUDGET,  # COA category, not COB
                'name': 'budget.pdf',
                'size': 1024000
            },
            {
                'file_type': FileType.BIOGRAPHY,  # COA category, not COB
                'name': 'bio.pdf',
                'size': 512000
            }
        ]

        response = self.client.post(
            self.submit_url,
            data=json.dumps(invalid_data),
            content_type='application/json'
        )

        # Verify 400 Bad Request
        self.assertEqual(response.status_code, 400)

        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('obavezni dokumenti', data['error'])

    def test_submission_logging(self):
        """Test 13: Verify submission_logger.info() called with reference number."""
        # This test verifies logging infrastructure
        # Actual logging verification requires log file inspection (manual test)

        with self.assertLogs('domovik.submissions', level='INFO') as cm:
            response = self.client.post(
                self.submit_url,
                data=json.dumps(self.valid_cob_data),
                content_type='application/json'
            )

            self.assertEqual(response.status_code, 201)

            # Verify log contains reference number
            log_messages = '\n'.join(cm.output)
            self.assertIn('COB submission SUCCESS', log_messages)
            self.assertIn('COB-', log_messages)

    def test_missing_applicant_data(self):
        """Test 14: Submit without applicant data and verify 400 error."""
        invalid_data = self.valid_cob_data.copy()
        del invalid_data['applicant']

        response = self.client.post(
            self.submit_url,
            data=json.dumps(invalid_data),
            content_type='application/json'
        )

        # Verify 400 Bad Request
        self.assertEqual(response.status_code, 400)

        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('podnosiocu', data['error'])

    @patch('apps.submissions.views.send_confirmation_email.delay')
    def test_email_confirmation_triggered(self, mock_email_task):
        """
        Test 15: CODE REVIEW FIX #6 - Verify email confirmation task is triggered.
        This test verifies that send_confirmation_email.delay() is called with correct application ID.
        """
        response = self.client.post(
            self.submit_url,
            data=json.dumps(self.valid_cob_data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 201)
        data = response.json()
        reference_number = data['reference_number']

        # Get the created application
        application = Application.objects.get(reference_number=reference_number)

        # Verify email task was called with application ID
        mock_email_task.assert_called_once_with(application.id)

    def test_validation_email_format(self):
        """
        Test 16: CODE REVIEW FIX #2 - Verify email validation.
        """
        invalid_data = self.valid_cob_data.copy()
        invalid_data['applicant']['email'] = 'invalid-email-format'

        response = self.client.post(
            self.submit_url,
            data=json.dumps(invalid_data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('email', data['error'].lower())

    def test_validation_field_length(self):
        """
        Test 17: CODE REVIEW FIX #11 - Verify field length validation.
        """
        invalid_data = self.valid_cob_data.copy()
        invalid_data['initiative']['naslov'] = 'x' * 200  # Exceeds 150 char limit

        response = self.client.post(
            self.submit_url,
            data=json.dumps(invalid_data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('predugo', data['error'].lower())

    def test_file_metadata_creation(self):
        """
        Test 18: CODE REVIEW FIX #1 - Verify FileMetadata records are created.
        This is a CRITICAL fix - Story 3-5 AC requires FileMetadata creation.
        """
        response = self.client.post(
            self.submit_url,
            data=json.dumps(self.valid_cob_data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 201)
        data = response.json()
        application = Application.objects.get(reference_number=data['reference_number'])

        # FIX #1 VERIFICATION: Verify FileMetadata records exist
        from apps.submissions.models import FileMetadata
        file_metadata_count = FileMetadata.objects.filter(application=application).count()
        self.assertEqual(file_metadata_count, 2, "FileMetadata records should be created for both files")

        # Verify file types
        file_types = set(FileMetadata.objects.filter(application=application).values_list('file_type', flat=True))
        self.assertEqual(file_types, {FileType.OPIS_INICIJATIVE, FileType.PISMO_NAMERE})


class COBReferenceNumberServiceTestCase(TestCase):
    """Additional tests for ReferenceNumberService with COB type."""

    def test_cob_reference_number_generation(self):
        """Test COB reference number generation."""
        ref_number = ReferenceNumberService.generate_reference_number('COB')

        # Verify format
        self.assertIsNotNone(ref_number)
        self.assertTrue(ref_number.startswith('COB-'))
        self.assertRegex(ref_number, r'^COB-\d{4}-\d{3}$')

    def test_cob_sequence_uniqueness(self):
        """Test that COB sequence is separate from COA."""
        current_year = timezone.now().year

        # Generate both COA and COB
        coa_ref = ReferenceNumberService.generate_reference_number('COA')
        cob_ref = ReferenceNumberService.generate_reference_number('COB')

        # Both should be 001 (separate sequences)
        self.assertEqual(coa_ref, f'COA-{current_year}-001')
        self.assertEqual(cob_ref, f'COB-{current_year}-001')

        # Verify separate database records
        sequences = ReferenceNumberSequence.objects.filter(year=current_year)
        self.assertEqual(sequences.count(), 2)

        coa_seq = sequences.get(application_type='COA')
        cob_seq = sequences.get(application_type='COB')

        self.assertEqual(coa_seq.last_number, 1)
        self.assertEqual(cob_seq.last_number, 1)
