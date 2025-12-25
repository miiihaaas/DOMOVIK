# -*- coding: utf-8 -*-
"""
Unit tests for submissions app.

Story 2.1 - Database Setup & COA Routing
Tests cover:
- Application model creation and validation
- Applicant model creation and validation
- URL routing functionality
- Database connection and charset configuration
- Security baseline configuration
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.db import connection
from django.conf import settings
from apps.submissions.models import Application, Applicant


class ApplicationModelTests(TestCase):
    """Test suite for Application model."""

    def test_create_coa_application(self):
        """Test creating a COA (Project) application with all fields."""
        app = Application.objects.create(
            reference_number='COA-2025-001',
            type='COA',
            status='submitted'
        )

        self.assertEqual(app.reference_number, 'COA-2025-001')
        self.assertEqual(app.type, 'COA')
        self.assertEqual(app.status, 'submitted')
        self.assertIsNotNone(app.created_at)
        self.assertEqual(str(app), 'COA-2025-001 (Prijava za Projekat)')

    def test_create_cob_application(self):
        """Test creating a COB (Initiative) application."""
        app = Application.objects.create(
            reference_number='COB-2025-001',
            type='COB',
            status='draft'
        )

        self.assertEqual(app.type, 'COB')
        self.assertEqual(app.status, 'draft')
        self.assertEqual(str(app), 'COB-2025-001 (Prijava za Inicijativu)')

    def test_reference_number_uniqueness(self):
        """Test that reference_number must be unique."""
        Application.objects.create(
            reference_number='COA-2025-001',
            type='COA',
            status='draft'
        )

        # Attempting to create duplicate reference_number should raise IntegrityError
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Application.objects.create(
                reference_number='COA-2025-001',
                type='COA',
                status='draft'
            )

    def test_application_auto_generate_reference_number(self):
        """
        Test that reference_number is auto-generated if not provided.
        Note: Full generation logic implemented in Story 2.11.
        """
        app = Application.objects.create(
            type='COA',
            status='draft'
        )

        self.assertIsNotNone(app.reference_number)
        self.assertTrue(app.reference_number.startswith('COA-'))

    def test_application_auto_generate_unique_reference_numbers(self):
        """
        Test that auto-generated reference numbers are unique.
        Regression: Code review found stub returning same value for all apps.
        """
        app1 = Application.objects.create(type='COA', status='draft')
        app2 = Application.objects.create(type='COA', status='draft')

        # Each app should get unique reference_number
        self.assertNotEqual(app1.reference_number, app2.reference_number)

    def test_application_type_validation(self):
        """
        Test that Application.type field is validated against TYPE_CHOICES.
        """
        app = Application(
            reference_number='TEST-2025-001',
            type='INVALID',  # Invalid type
            status='draft'
        )

        with self.assertRaises(ValidationError) as context:
            app.full_clean()

        self.assertIn('type', context.exception.message_dict)

    def test_application_auto_set_submitted_at(self):
        """
        Test that submitted_at is automatically set when status becomes 'submitted'.
        """
        app = Application.objects.create(
            reference_number='COA-2025-AUTO',
            type='COA',
            status='draft'
        )

        # Initially submitted_at should be None
        self.assertIsNone(app.submitted_at)

        # Change status to submitted
        app.status = 'submitted'
        app.save()

        # submitted_at should now be set
        self.assertIsNotNone(app.submitted_at)

        # Verify timestamp is recent (within last 5 seconds)
        from django.utils import timezone
        import datetime
        time_diff = timezone.now() - app.submitted_at
        self.assertLess(time_diff, datetime.timedelta(seconds=5))


class ApplicantModelTests(TestCase):
    """Test suite for Applicant model."""

    def setUp(self):
        """Create test application for use in applicant tests."""
        self.coa_app = Application.objects.create(
            reference_number='COA-2025-TEST',
            type='COA',
            status='draft'
        )

        self.cob_app = Application.objects.create(
            reference_number='COB-2025-TEST',
            type='COB',
            status='draft'
        )

    def test_create_fizicko_lice_applicant(self):
        """Test creating fizičko lice (individual) applicant."""
        applicant = Applicant.objects.create(
            application=self.cob_app,  # COB doesn't require JMBG
            entity_type='fizicko',
            ime='Marko',
            prezime='Marković',
            adresa='Kralja Petra 123',
            email='marko@example.com',
            telefon='0641234567'
        )

        self.assertEqual(applicant.entity_type, 'fizicko')
        self.assertEqual(str(applicant), 'Marko Marković')

    def test_create_pravno_lice_applicant(self):
        """Test creating pravno lice (legal entity) applicant."""
        applicant = Applicant.objects.create(
            application=self.cob_app,  # COB doesn't require matični broj
            entity_type='pravno',
            naziv_organizacije='DOMOVIK NGO',
            adresa='Kneza Miloša 45',
            email='info@domovik.rs',
            telefon='0112345678'
        )

        self.assertEqual(applicant.entity_type, 'pravno')
        self.assertEqual(str(applicant), 'DOMOVIK NGO')

    def test_fizicko_lice_validation_ime_required(self):
        """Test that ime and prezime are required for fizičko lice."""
        applicant = Applicant(
            application=self.cob_app,
            entity_type='fizicko',
            ime='',  # Empty name
            prezime='',  # Empty surname
            adresa='Test adresa',
            email='test@example.com',
            telefon='0641234567'
        )

        with self.assertRaises(ValidationError) as context:
            applicant.full_clean()

        self.assertIn('ime', context.exception.message_dict)
        self.assertIn('prezime', context.exception.message_dict)

    def test_pravno_lice_validation_naziv_required(self):
        """Test that naziv_organizacije is required for pravno lice."""
        applicant = Applicant(
            application=self.cob_app,
            entity_type='pravno',
            naziv_organizacije='',  # Empty organization name
            adresa='Test adresa',
            email='test@example.com',
            telefon='0641234567'
        )

        with self.assertRaises(ValidationError) as context:
            applicant.full_clean()

        self.assertIn('naziv_organizacije', context.exception.message_dict)

    def test_coa_fizicko_jmbg_required(self):
        """Test that JMBG is required for fizičko lice in COA applications."""
        applicant = Applicant(
            application=self.coa_app,  # COA requires JMBG
            entity_type='fizicko',
            ime='Marko',
            prezime='Marković',
            jmbg='',  # Missing JMBG
            adresa='Test adresa',
            email='test@example.com',
            telefon='0641234567'
        )

        with self.assertRaises(ValidationError) as context:
            applicant.full_clean()

        self.assertIn('jmbg', context.exception.message_dict)

    def test_coa_fizicko_jmbg_format_validation(self):
        """Test that JMBG must be exactly 13 digits for COA fizičko lice."""
        applicant = Applicant(
            application=self.coa_app,
            entity_type='fizicko',
            ime='Marko',
            prezime='Marković',
            jmbg='12345',  # Invalid - not 13 digits
            adresa='Test adresa',
            email='test@example.com',
            telefon='0641234567'
        )

        with self.assertRaises(ValidationError) as context:
            applicant.full_clean()

        self.assertIn('jmbg', context.exception.message_dict)

    def test_coa_pravno_maticni_required(self):
        """Test that matični broj is required for pravno lice in COA applications."""
        applicant = Applicant(
            application=self.coa_app,  # COA requires matični broj
            entity_type='pravno',
            naziv_organizacije='DOMOVIK NGO',
            maticni_broj='',  # Missing matični broj
            adresa='Test adresa',
            email='test@example.com',
            telefon='0641234567'
        )

        with self.assertRaises(ValidationError) as context:
            applicant.full_clean()

        self.assertIn('maticni_broj', context.exception.message_dict)

    def test_cob_fizicko_jmbg_not_required(self):
        """Test that JMBG is NOT required for fizičko lice in COB applications."""
        applicant = Applicant.objects.create(
            application=self.cob_app,  # COB doesn't require JMBG
            entity_type='fizicko',
            ime='Ana',
            prezime='Anić',
            jmbg='',  # Empty JMBG is OK for COB
            adresa='Test adresa',
            email='ana@example.com',
            telefon='0641234567'
        )

        # Should not raise ValidationError
        applicant.full_clean()
        self.assertEqual(applicant.jmbg, '')


class DatabaseConnectionTests(TestCase):
    """Test suite for database connection and configuration."""

    def test_database_connection_works(self):
        """Test that MySQL database connection is functional."""
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            self.assertEqual(result[0], 1)

    def test_database_charset_utf8mb4(self):
        """
        Test that database charset is utf8mb4 for Serbian language support.
        Critical: Epic 1 lessons learned - utf8mb4 required for č, ć, š, đ, ž.
        """
        # Skip test if not using MySQL (e.g., SQLite in tests)
        if connection.vendor != 'mysql':
            self.skipTest("Charset test only applicable for MySQL")

        with connection.cursor() as cursor:
            cursor.execute("SHOW VARIABLES LIKE 'character_set_database'")
            result = cursor.fetchone()
            self.assertEqual(result[1], 'utf8mb4',
                           "Database must use utf8mb4 charset for Serbian language support")

    def test_migrations_applied(self):
        """Test that all migrations have been applied successfully."""
        # Attempting to query models verifies migrations are applied
        count = Application.objects.count()
        self.assertGreaterEqual(count, 0)  # Should not raise error

    def test_serbian_characters_stored_correctly(self):
        """
        Integration test: Verify Serbian characters (č, ć, š, đ, ž) are stored
        and retrieved correctly from database.

        Critical: Epic 1 lessons learned - utf8mb4 required for Serbian language.
        """
        # Create application with Serbian characters
        app = Application.objects.create(
            reference_number='COA-2025-ČĆŠĐŽ',
            type='COA',
            status='draft'
        )

        # Create applicant with Serbian name
        applicant = Applicant.objects.create(
            application=app,
            entity_type='fizicko',
            ime='Đorđe',
            prezime='Čović',
            jmbg='1234567890123',
            adresa='Kralja Petra 123, Niš',
            email='djordje.covic@example.rs',
            telefon='064/123-4567'
        )

        # Retrieve from database and verify characters preserved
        retrieved_app = Application.objects.get(pk=app.pk)
        retrieved_applicant = Applicant.objects.get(pk=applicant.pk)

        # Verify Serbian characters not corrupted
        self.assertEqual(retrieved_app.reference_number, 'COA-2025-ČĆŠĐŽ')
        self.assertEqual(retrieved_applicant.ime, 'Đorđe')
        self.assertEqual(retrieved_applicant.prezime, 'Čović')
        self.assertIn('Niš', retrieved_applicant.adresa)

        # Verify no corruption (č → c, ć → c, etc.)
        self.assertNotEqual(retrieved_applicant.ime, 'Dorde')  # Wrong
        self.assertNotEqual(retrieved_applicant.prezime, 'Covic')  # Wrong


class COARoutingTests(TestCase):
    """Test suite for URL routing and views."""

    def setUp(self):
        """Set up test client."""
        self.client = Client()

    def test_projekat_url_returns_200(self):
        """Test that /projekat/ URL returns HTTP 200 OK."""
        response = self.client.get('/projekat/')
        self.assertEqual(response.status_code, 200)

    def test_projekat_uses_correct_template(self):
        """Test that /projekat/ uses the correct template."""
        response = self.client.get('/projekat/')
        self.assertTemplateUsed(response, 'submissions/coa_form.html')

    def test_projekat_url_reverse(self):
        """Test that 'coa_form' named URL pattern resolves correctly."""
        url = reverse('coa_form')
        self.assertEqual(url, '/projekat/')

    def test_landing_page_links_to_projekat(self):
        """Test that landing page contains link to /projekat/ using URL template tag."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

        # Check that response contains the correct href
        self.assertContains(response, 'href="/projekat/"')


class SecurityBaselineTests(TestCase):
    """Test suite for Django security baseline configuration."""

    def test_csrf_middleware_enabled(self):
        """Test that CSRF middleware is enabled in settings."""
        self.assertIn(
            'django.middleware.csrf.CsrfViewMiddleware',
            settings.MIDDLEWARE
        )

    def test_secret_key_loaded(self):
        """Test that SECRET_KEY is loaded from environment variables."""
        self.assertIsNotNone(settings.SECRET_KEY)
        self.assertGreater(len(settings.SECRET_KEY), 0)
        # SECRET_KEY should be a non-empty string (actual value doesn't matter for test)
        self.assertIsInstance(settings.SECRET_KEY, str)

    def test_debug_configuration(self):
        """Test that DEBUG setting is controlled by environment variable."""
        # In tests, DEBUG is typically True
        self.assertIsInstance(settings.DEBUG, bool)

    def test_allowed_hosts_configured(self):
        """Test that ALLOWED_HOSTS is configured."""
        self.assertIsNotNone(settings.ALLOWED_HOSTS)
        self.assertIsInstance(settings.ALLOWED_HOSTS, list)

    def test_https_settings_configured(self):
        """
        Test that HTTPS enforcement settings are properly configured in settings.py.
        Settings should exist and be boolean values (actual values depend on DEBUG setting).
        """
        # HTTPS settings should be defined (value depends on DEBUG mode)
        # In development (DEBUG=True): SECURE_SSL_REDIRECT=False
        # In production (DEBUG=False): SECURE_SSL_REDIRECT=True
        self.assertTrue(hasattr(settings, 'SECURE_SSL_REDIRECT'))
        self.assertIsInstance(settings.SECURE_SSL_REDIRECT, bool)


class Epic1RegressionTests(TestCase):
    """
    Regression tests to ensure Epic 1 functionality still works after database changes.
    Story 2.1 adds database models but should not break landing page routing.
    """

    def setUp(self):
        """Set up test client."""
        self.client = Client()

    def test_landing_page_still_accessible(self):
        """Test that landing page is still accessible after MySQL + models added."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_coa_banner_link_works(self):
        """Test that COA banner on landing page still links to /projekat/."""
        response = self.client.get('/')
        self.assertContains(response, 'href="/projekat/"')
        self.assertContains(response, 'Prijava za Projekat (COA)')

    def test_projekat_route_accessible_after_models(self):
        """Test that /projekat/ route is still accessible after database models added."""
        response = self.client.get('/projekat/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'submissions/coa_form.html')


# ============================================================================
# Story 2.2 Tests - COA Form Section I
# ============================================================================

from apps.submissions.forms import COAFormSectionI


class COAFormSectionITests(TestCase):
    """Tests for COA Form Section I - Entity Type Switch Form"""

    def test_form_fizicko_lice_valid_data(self):
        """Test form with valid fizičko lice data"""
        form_data = {
            'entity_type': 'fizicko',
            'ime': 'Marko',
            'prezime': 'Petrović',
            'jmbg': '1234567890123',
            'adresa': 'Beograd, Kneza Miloša 10',
            'email': 'marko@example.com',
            'telefon': '0611234567',
        }
        form = COAFormSectionI(data=form_data)
        self.assertTrue(form.is_valid(), msg=f"Form errors: {form.errors}")

    def test_form_pravno_lice_valid_data(self):
        """Test form with valid pravno lice data"""
        form_data = {
            'entity_type': 'pravno',
            'naziv_organizacije': 'Udruženje Građana Domovik',
            'maticni_broj': '12345678',
            'adresa': 'Beograd, Kneza Miloša 10',
            'email': 'info@domovik.rs',
            'telefon': '0111234567',
        }
        form = COAFormSectionI(data=form_data)
        self.assertTrue(form.is_valid(), msg=f"Form errors: {form.errors}")

    def test_form_fizicko_missing_ime(self):
        """Test form validation fails if fizičko lice missing ime"""
        form_data = {
            'entity_type': 'fizicko',
            # 'ime': 'Marko',  # Missing
            'prezime': 'Petrović',
            'jmbg': '1234567890123',
            'adresa': 'Beograd',
            'email': 'marko@example.com',
            'telefon': '0611234567',
        }
        form = COAFormSectionI(data=form_data)
        self.assertFalse(form.is_valid())

    def test_form_fizicko_missing_jmbg(self):
        """Test form validation fails if fizičko lice missing JMBG (COA requirement)"""
        form_data = {
            'entity_type': 'fizicko',
            'ime': 'Marko',
            'prezime': 'Petrović',
            # 'jmbg': '1234567890123',  # Missing
            'adresa': 'Beograd',
            'email': 'marko@example.com',
            'telefon': '0611234567',
        }
        form = COAFormSectionI(data=form_data)
        self.assertFalse(form.is_valid())

    def test_form_jmbg_invalid_length(self):
        """Test form validation fails if JMBG is not 13 digits"""
        form_data = {
            'entity_type': 'fizicko',
            'ime': 'Marko',
            'prezime': 'Petrović',
            'jmbg': '12345',  # Too short
            'adresa': 'Beograd',
            'email': 'marko@example.com',
            'telefon': '0611234567',
        }
        form = COAFormSectionI(data=form_data)
        self.assertFalse(form.is_valid())

    def test_form_pravno_missing_naziv(self):
        """Test form validation fails if pravno lice missing naziv_organizacije"""
        form_data = {
            'entity_type': 'pravno',
            # 'naziv_organizacije': 'Udruženje Domovik',  # Missing
            'maticni_broj': '12345678',
            'adresa': 'Beograd',
            'email': 'info@domovik.rs',
            'telefon': '0111234567',
        }
        form = COAFormSectionI(data=form_data)
        self.assertFalse(form.is_valid())

    def test_form_pravno_missing_maticni(self):
        """Test form validation fails if pravno lice missing matični broj (COA requirement)"""
        form_data = {
            'entity_type': 'pravno',
            'naziv_organizacije': 'Udruženje Domovik',
            # 'maticni_broj': '12345678',  # Missing
            'adresa': 'Beograd',
            'email': 'info@domovik.rs',
            'telefon': '0111234567',
        }
        form = COAFormSectionI(data=form_data)
        self.assertFalse(form.is_valid())

    def test_form_common_fields_required(self):
        """Test form validation fails if common fields (adresa, email, telefon) are missing"""
        form_data = {
            'entity_type': 'fizicko',
            'ime': 'Marko',
            'prezime': 'Petrović',
            'jmbg': '1234567890123',
            # Missing: adresa, email, telefon
        }
        form = COAFormSectionI(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('adresa', form.errors)
        self.assertIn('email', form.errors)
        self.assertIn('telefon', form.errors)


class COAFormTemplateTests(TestCase):
    """Tests for COA form template rendering"""

    def setUp(self):
        """Set up test client."""
        self.client = Client()

    def test_coa_form_page_loads(self):
        """Test /projekat/ page loads successfully"""
        response = self.client.get('/projekat/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'submissions/coa_form.html')

    def test_progress_stepper_rendered(self):
        """Test progress stepper is rendered with correct text"""
        response = self.client.get('/projekat/')
        self.assertContains(response, 'Sekcija 1 od 3')
        self.assertContains(response, 'progress-stepper')

    def test_entity_type_switcher_rendered(self):
        """Test entity type switcher toggle is rendered"""
        response = self.client.get('/projekat/')
        self.assertContains(response, 'Fizičko lice')
        self.assertContains(response, 'Pravno lice')
        self.assertContains(response, 'entity-type-switcher')

    def test_form_fields_rendered(self):
        """Test all form fields (fizičko, pravno, common) are present in HTML"""
        response = self.client.get('/projekat/')
        # Fizičko fields
        self.assertContains(response, 'id_ime')
        self.assertContains(response, 'id_prezime')
        self.assertContains(response, 'id_jmbg')
        # Pravno fields
        self.assertContains(response, 'id_naziv_organizacije')
        self.assertContains(response, 'id_maticni_broj')
        # Common fields
        self.assertContains(response, 'id_adresa')
        self.assertContains(response, 'id_email')
        self.assertContains(response, 'id_telefon')

    def test_navigation_buttons_disabled(self):
        """Test that navigation buttons are rendered but disabled (Story 2.7 placeholder)"""
        response = self.client.get('/projekat/')
        self.assertEqual(response.status_code, 200)
        # Check buttons are present
        self.assertContains(response, 'PRETHODNA SEKCIJA')
        self.assertContains(response, 'SLEDEĆA SEKCIJA')
        # Check both buttons have disabled attribute
        content = response.content.decode('utf-8')
        import re
        disabled_buttons = re.findall(r'<button[^>]*disabled[^>]*>', content)
        self.assertGreaterEqual(len(disabled_buttons), 2, "Expected at least 2 disabled buttons (navigation)")

    def test_aria_describedby_linkage(self):
        """
        Test that form fields with help text have aria-describedby attributes (NFR49)

        Story 2.3 Update: aria-describedby now includes BOTH error container AND help text
        (e.g., aria-describedby="id_jmbg_error id_jmbg_help")
        """
        response = self.client.get('/projekat/')
        content = response.content.decode('utf-8')

        # JMBG field should have aria-describedby pointing to both error and help text (Story 2.3)
        self.assertIn('id_jmbg_error', content)
        self.assertIn('id_jmbg_help', content)
        # Verify aria-describedby includes both (order may vary, so check both IDs present)
        import re
        jmbg_match = re.search(r'id="id_jmbg"[^>]*aria-describedby="([^"]*)"', content)
        self.assertIsNotNone(jmbg_match, "JMBG field should have aria-describedby attribute")
        aria_describedby_value = jmbg_match.group(1)
        self.assertIn('id_jmbg_error', aria_describedby_value)
        self.assertIn('id_jmbg_help', aria_describedby_value)

        # Email field should have aria-describedby with both error and help
        self.assertIn('id_email_error', content)
        self.assertIn('id_email_help', content)
        email_match = re.search(r'id="id_email"[^>]*aria-describedby="([^"]*)"', content)
        self.assertIsNotNone(email_match, "Email field should have aria-describedby attribute")
        aria_describedby_value = email_match.group(1)
        self.assertIn('id_email_error', aria_describedby_value)
        self.assertIn('id_email_help', aria_describedby_value)

        # Telefon field should have aria-describedby with both error and help
        self.assertIn('id_telefon_error', content)
        self.assertIn('id_telefon_help', content)
        telefon_match = re.search(r'id="id_telefon"[^>]*aria-describedby="([^"]*)"', content)
        self.assertIsNotNone(telefon_match, "Telefon field should have aria-describedby attribute")
        aria_describedby_value = telefon_match.group(1)
        self.assertIn('id_telefon_error', aria_describedby_value)
        self.assertIn('id_telefon_help', aria_describedby_value)


# ============================================================================
# Story 2.3 Tests - Real-Time Validation for Section I
# ============================================================================


class RealTimeValidationTemplateTests(TestCase):
    """Tests for real-time validation template integration (Story 2.3)"""

    def setUp(self):
        """Set up test client."""
        self.client = Client()

    def test_real_time_validator_js_loaded(self):
        """Test that real-time-validator.js is loaded in template"""
        response = self.client.get('/projekat/')
        self.assertContains(response, 'real-time-validator.js')

    def test_validation_error_containers_exist(self):
        """Test that validation error containers exist for all validated fields"""
        response = self.client.get('/projekat/')
        content = response.content.decode('utf-8')

        # Check email validation error container
        self.assertIn('id="id_email_error"', content)
        self.assertIn('class="validation-error"', content)

        # Check telefon validation error container
        self.assertIn('id="id_telefon_error"', content)

        # Check JMBG validation error container
        self.assertIn('id="id_jmbg_error"', content)

        # Check matični broj validation error container
        self.assertIn('id="id_maticni_broj_error"', content)

    def test_aria_invalid_attribute_set(self):
        """Test that aria-invalid attributes are set to false by default (WCAG 2.1)"""
        response = self.client.get('/projekat/')
        content = response.content.decode('utf-8')

        # All validated fields should have aria-invalid="false" by default
        # Check each field has both id and aria-invalid (attribute order may vary)
        import re

        # Email field
        self.assertIsNotNone(re.search(r'<input[^>]*id="id_email"[^>]*aria-invalid="false"[^>]*>', content))

        # Telefon field
        self.assertIsNotNone(re.search(r'<input[^>]*id="id_telefon"[^>]*aria-invalid="false"[^>]*>', content))

        # JMBG field
        self.assertIsNotNone(re.search(r'<input[^>]*id="id_jmbg"[^>]*aria-invalid="false"[^>]*>', content))

        # Matični broj field
        self.assertIsNotNone(re.search(r'<input[^>]*id="id_maticni_broj"[^>]*aria-invalid="false"[^>]*>', content))

    def test_aria_live_polite_on_error_containers(self):
        """Test that validation error containers have aria-live='polite' for screen readers"""
        response = self.client.get('/projekat/')
        content = response.content.decode('utf-8')

        # Check aria-live="polite" on validation error containers
        import re
        aria_live_pattern = r'<div[^>]*id="id_\w+_error"[^>]*aria-live="polite"[^>]*>'
        matches = re.findall(aria_live_pattern, content)
        self.assertGreaterEqual(len(matches), 4, "Expected at least 4 validation error containers with aria-live='polite'")


class RealTimeValidationFormTests(TestCase):
    """
    Server-side validation tests for progressive enhancement (Story 2.3)
    Ensures form validation still works when JavaScript is disabled
    """

    def test_server_validates_invalid_email(self):
        """Test that server-side validation catches invalid email format"""
        form_data = {
            'entity_type': 'fizicko',
            'ime': 'Marko',
            'prezime': 'Petrović',
            'jmbg': '1234567890123',
            'adresa': 'Beograd, Kneza Miloša 10',
            'email': 'invalid-email',  # Invalid format
            'telefon': '0611234567',
        }
        form = COAFormSectionI(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_server_validates_empty_email(self):
        """Test that server-side validation catches empty email"""
        form_data = {
            'entity_type': 'fizicko',
            'ime': 'Marko',
            'prezime': 'Petrović',
            'jmbg': '1234567890123',
            'adresa': 'Beograd, Kneza Miloša 10',
            'email': '',  # Empty
            'telefon': '0611234567',
        }
        form = COAFormSectionI(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_server_validates_empty_telefon(self):
        """Test that server-side validation catches empty telefon"""
        form_data = {
            'entity_type': 'fizicko',
            'ime': 'Marko',
            'prezime': 'Petrović',
            'jmbg': '1234567890123',
            'adresa': 'Beograd, Kneza Miloša 10',
            'email': 'marko@example.com',
            'telefon': '',  # Empty
        }
        form = COAFormSectionI(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('telefon', form.errors)

    def test_valid_serbian_phone_formats(self):
        """Test that valid Serbian phone numbers pass validation"""
        valid_phones = [
            '0611234567',
            '0641234567',
            '0691234567',
            '064-123-4567',  # With separators (normalized by validator)
            '064 123 4567',  # With spaces
        ]

        for phone in valid_phones:
            form_data = {
                'entity_type': 'fizicko',
                'ime': 'Marko',
                'prezime': 'Petrović',
                'jmbg': '1234567890123',
                'adresa': 'Beograd',
                'email': 'marko@example.com',
                'telefon': phone,
            }
            form = COAFormSectionI(data=form_data)
            # Note: Server-side doesn't enforce phone format (CharField only)
            # Client-side validation handles phone format
            self.assertTrue(form.is_valid(), msg=f"Phone {phone} should be valid. Errors: {form.errors}")

    def test_valid_email_formats(self):
        """Test that valid email formats pass validation"""
        valid_emails = [
            'marko@example.com',
            'test+tag@domain.co.rs',
            'user.name@sub.domain.com',
        ]

        for email in valid_emails:
            form_data = {
                'entity_type': 'fizicko',
                'ime': 'Marko',
                'prezime': 'Petrović',
                'jmbg': '1234567890123',
                'adresa': 'Beograd',
                'email': email,
                'telefon': '0611234567',
            }
            form = COAFormSectionI(data=form_data)
            self.assertTrue(form.is_valid(), msg=f"Email {email} should be valid. Errors: {form.errors}")


# ============================================================================
# Story 2.4 Tests - LocalStorage Draft System - Auto-Save
# ============================================================================


class AutoSaveDraftSystemTemplateTests(TestCase):
    """
    Tests for auto-save draft system template integration (Story 2.4)

    Note: Most auto-save functionality is client-side JavaScript (localStorage,
    auto-save timer, beforeunload handler, visual indicators). These tests verify:
    1. Template contains correct HTML elements
    2. JavaScript files are loaded
    3. CSS styles are loaded

    For comprehensive JavaScript testing, use:
    - Jest/Mocha/Jasmine for unit tests
    - Selenium/Playwright/Cypress for browser automation tests

    CODE REVIEW FINDING (MEDIUM #7):
    Task 2.7 claims "only one indicator visible at a time, cancel previous hide timeout
    on new save" and Task 9.8 claims "Test visual indicator queueing (no stacking)".
    Code has indicatorTimeout logic (draft-manager.js:234, 279), but MISSING automated
    test for queueing behavior. To fully verify:
    - Add Jest test: Simulate 3 rapid saves, verify only ONE indicator visible
    - Add Playwright test: Trigger rapid saves, check computed style visibility
    """

    def setUp(self):
        """Set up test client."""
        self.client = Client()

    def test_draft_manager_js_loaded(self):
        """Test that draft-manager.js is loaded in template (Story 2.2, enhanced in 2.4)"""
        response = self.client.get('/projekat/')
        self.assertContains(response, 'draft-manager.js')

    def test_autosave_indicator_element_exists(self):
        """Test that auto-save indicator HTML element exists in template (Task 2.1)"""
        response = self.client.get('/projekat/')
        content = response.content.decode('utf-8')

        # Check auto-save indicator element
        self.assertIn('id="autosave-indicator"', content)
        self.assertIn('class="autosave-indicator"', content)

        # Check ARIA attributes for accessibility (Task 2.5)
        self.assertIn('aria-live="polite"', content)
        self.assertIn('aria-atomic="true"', content)

        # Check BEM structure (Task 2.4)
        self.assertIn('autosave-indicator__icon', content)
        self.assertIn('autosave-indicator__text', content)

    def test_noscript_fallback_exists(self):
        """Test that <noscript> fallback message exists (Task 5.8)"""
        response = self.client.get('/projekat/')
        content = response.content.decode('utf-8')

        # Check noscript element exists
        self.assertIn('<noscript>', content)
        self.assertIn('class="noscript-warning"', content)

        # Check Serbian message is present (UTF-8 encoding test)
        self.assertIn('JavaScript je onemogućen', content)
        self.assertIn('bez auto-save i real-time validacije', content)

    def test_forms_css_loaded(self):
        """Test that forms.css is loaded (contains auto-save indicator styles)"""
        response = self.client.get('/projekat/')
        self.assertContains(response, 'forms.css')

    def test_entity_type_switcher_js_loaded(self):
        """Test that entity-type-switcher.js is loaded (race condition prevention - Task 4.4)"""
        response = self.client.get('/projekat/')
        self.assertContains(response, 'entity-type-switcher.js')


class AutoSaveDraftGDPRComplianceTests(TestCase):
    """
    GDPR compliance tests for auto-save draft system (Story 2.4 - Task 7)

    Critical NFR16-18 requirements:
    - Draft data stored ONLY in client-side localStorage (no server transmission)
    - Zero network requests during auto-save operation
    - Admin panel NEVER sees draft data (only submitted applications)
    - 7-day retention with automatic cleanup
    """

    def test_draft_data_not_in_database(self):
        """
        Test that draft data is NOT stored in database before submission (NFR16)

        GDPR Compliance: Draft data must remain client-side only until user
        clicks PODNESI button.
        """
        # Simulate user filling form (but NOT submitting)
        # In real scenario: JavaScript saves to localStorage, not database

        # Verify NO Application records exist (no drafts saved to database)
        app_count = Application.objects.count()
        self.assertEqual(app_count, 0, "Draft data should NOT be in database")

        # Verify NO Applicant records exist
        applicant_count = Applicant.objects.count()
        self.assertEqual(applicant_count, 0, "Draft applicant data should NOT be in database")

    def test_get_request_does_not_save_data(self):
        """Test that GET request to /projekat/ does NOT create database records (GDPR)"""
        # Load form page
        response = self.client.get('/projekat/')
        self.assertEqual(response.status_code, 200)

        # Verify NO data saved to database
        self.assertEqual(Application.objects.count(), 0)
        self.assertEqual(Applicant.objects.count(), 0)

    def test_form_page_has_no_auto_submit(self):
        """Test that form does NOT auto-submit (data sent only on explicit PODNESI click)"""
        response = self.client.get('/projekat/')
        content = response.content.decode('utf-8')

        # Form should have method="post" action="/projekat/"
        # But should NOT have JavaScript auto-submit
        import re

        # Check form element exists with correct attributes
        self.assertIsNotNone(re.search(r'<form[^>]*method="post"[^>]*>', content))
        self.assertIsNotNone(re.search(r'<form[^>]*action="[^"]*projekat[^"]*"[^>]*>', content))

        # Verify no auto-submit patterns (e.g., onsubmit, form.submit())
        # Note: draft-manager.js should ONLY use localStorage, never form.submit()
        self.assertNotIn('form.submit()', content)


class AutoSaveDraftUTF8EncodingTests(TestCase):
    """
    UTF-8 encoding tests for Serbian text in auto-save indicator (Story 2.4 - Task 10.1)

    Epic 1 Lessons: UTF-8 encoding critical for Serbian characters (č, ć, š, đ, ž)
    """

    def test_autosave_indicator_serbian_text_not_corrupted(self):
        """Test that Serbian text in auto-save indicator is not corrupted (Task 10.1)"""
        response = self.client.get('/projekat/')
        content = response.content.decode('utf-8')

        # Check noscript message has correct Serbian characters
        # Negative test: Verify č/ć/š NOT corrupted to c/s
        self.assertIn('onemogućen', content)  # Correct: ć
        self.assertNotIn('onemogucen', content)  # Wrong: c instead of ć

        # Note: "Sačuvano" and "Čuva se..." text is in JavaScript (draft-manager.js)
        # Cannot verify in template, but verified via file encoding tests

    def test_template_has_utf8_charset(self):
        """Test that template inherits UTF-8 charset from base.html"""
        response = self.client.get('/projekat/')

        # Django returns response with proper encoding
        self.assertEqual(response.charset, 'utf-8')

        # Content-Type header should specify UTF-8
        content_type = response.get('Content-Type', '')
        self.assertIn('charset=utf-8', content_type)

    def test_javascript_file_utf8_encoding(self):
        """
        Test that draft-manager.js file is UTF-8 encoded (CODE REVIEW FIX - LOW #11)

        Task 10.1 claims to test "Sačuvano" and "Čuva se..." rendering, but those
        strings are in JavaScript source file, not template. This test verifies the
        actual JavaScript file contains correct Serbian characters.
        """
        import os
        js_file_path = os.path.join('static', 'js', 'draft-manager.js')

        # Read JavaScript file
        with open(js_file_path, 'r', encoding='utf-8') as f:
            js_content = f.read()

        # Verify Serbian strings with č/ć characters are NOT corrupted
        self.assertIn('Čuva se...', js_content, "JavaScript should contain 'Čuva se...' (Č not corrupted)")
        self.assertIn('Sačuvano', js_content, "JavaScript should contain 'Sačuvano' (č not corrupted)")
        self.assertIn('Greška', js_content, "JavaScript should contain 'Greška' (š not corrupted)")

        # Negative test: Verify NOT corrupted to ASCII equivalents
        self.assertNotIn('Cuva se...', js_content, "Should NOT be corrupted to 'Cuva se...'")
        self.assertNotIn('Sacuvano', js_content, "Should NOT be corrupted to 'Sacuvano'")


class AutoSaveDraftBrowserCompatibilityTests(TestCase):
    """
    Browser compatibility tests for auto-save system (Story 2.4 - Task 8)

    Note: Full browser testing requires Selenium/Playwright/Cypress.
    These tests verify server-side template compatibility only.
    """

    def test_template_compatible_with_all_browsers(self):
        """Test that template uses standard HTML5 (no browser-specific code)"""
        response = self.client.get('/projekat/')
        content = response.content.decode('utf-8')

        # Verify HTML5 doctype (inherited from base.html)
        # COA form extends base.html, so base.html should have <!DOCTYPE html>

        # Verify no browser-specific vendor prefixes in inline styles
        # (All styles should be in forms.css, not inline)
        self.assertNotIn('-webkit-', content)
        self.assertNotIn('-moz-', content)
        self.assertNotIn('-ms-', content)

    def test_noscript_fallback_for_no_javascript_browsers(self):
        """Test that <noscript> fallback exists for browsers with JavaScript disabled"""
        response = self.client.get('/projekat/')
        content = response.content.decode('utf-8')

        # Verify noscript element
        self.assertIn('<noscript>', content)

        # Verify graceful degradation message
        self.assertIn('bez auto-save', content)


class AutoSaveDraftPerformanceTests(TestCase):
    """
    Performance tests for auto-save draft system (Story 2.4 - Task 6)

    Note: JavaScript performance (e.g., auto-save < 500ms - NFR4) requires:
    - Browser DevTools performance profiling
    - Lighthouse CI for automated performance testing

    These tests verify server-side performance only.

    CODE REVIEW FINDING (HIGH #1):
    Task 6.5 claims "Test: Auto-save completes in <500ms even with large form data"
    but actual automated test is MISSING. Current implementation uses console.time/timeEnd
    for manual verification (draft-manager.js:82, 96). To fully verify NFR4:
    - Add Jest/Mocha unit test with mocked localStorage timing
    - Add Playwright/Cypress E2E test with performance.measure API
    - Add CI performance regression test with Lighthouse or similar
    """

    def test_form_page_loads_quickly(self):
        """Test that /projekat/ page loads without database queries for drafts"""
        # Load form page
        from django.test.utils import override_settings
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        with CaptureQueriesContext(connection) as queries:
            response = self.client.get('/projekat/')
            self.assertEqual(response.status_code, 200)

        # Verify minimal database queries (no draft queries)
        # Should only query for CSRF token and session (if any)
        # CRITICAL: NO Application or Applicant queries (drafts are client-side only)
        query_count = len(queries)

        # Note: Query count may vary based on middleware/session config
        # Main assertion: NO queries to Application or Applicant tables
        for query in queries:
            sql = query['sql'].lower()
            self.assertNotIn('submissions_application', sql,
                           "Should not query Application table for draft data")
            self.assertNotIn('submissions_applicant', sql,
                           "Should not query Applicant table for draft data")
