# -*- coding: utf-8 -*-
"""
Unit tests for Django Forms.
Story 3.2: COBApplicantForm - Simplified applicant validation (no JMBG/matični broj)
"""
from django.test import TestCase
from apps.submissions.forms import COBApplicantForm


class COBApplicantFormTests(TestCase):
    """Test suite for COBApplicantForm validation."""

    def test_valid_fizicko_lice(self):
        """Test valid fizičko lice data passes validation."""
        form = COBApplicantForm({
            'entity_type': 'fizicko',
            'ime': 'Marko',
            'prezime': 'Petrović',
            'adresa': 'Beograd, Kneza Miloša 10',
            'email': 'marko@example.com',
            'telefon': '0651234568',  # ISSUE 2 FIX: 8 digits after 6 (was 7)
        })
        self.assertTrue(form.is_valid())

    def test_valid_pravno_lice(self):
        """Test valid pravno lice data passes validation."""
        form = COBApplicantForm({
            'entity_type': 'pravno',
            'naziv_organizacije': 'Udruženje građana Domovik',
            'adresa': 'Novi Sad, Zmaj Jovina 5',
            'email': 'info@domovik.rs',
            'telefon': '+381651234568',  # ISSUE 2 FIX: 8 digits after 6 (was 7)
        })
        self.assertTrue(form.is_valid())

    def test_fizicko_missing_ime(self):
        """Test fizičko lice without ime fails validation."""
        form = COBApplicantForm({
            'entity_type': 'fizicko',
            'ime': '',  # Missing
            'prezime': 'Petrović',
            'adresa': 'Beograd',
            'email': 'test@example.com',
            'telefon': '0651234568',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('ime', form.errors)

    def test_fizicko_missing_prezime(self):
        """Test fizičko lice without prezime fails validation."""
        form = COBApplicantForm({
            'entity_type': 'fizicko',
            'ime': 'Marko',
            'prezime': '',  # Missing
            'adresa': 'Beograd',
            'email': 'test@example.com',
            'telefon': '0651234568',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('prezime', form.errors)

    def test_pravno_missing_naziv(self):
        """Test pravno lice without naziv_organizacije fails validation."""
        form = COBApplicantForm({
            'entity_type': 'pravno',
            'naziv_organizacije': '',  # Missing
            'adresa': 'Novi Sad',
            'email': 'test@example.com',
            'telefon': '0651234568',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('naziv_organizacije', form.errors)

    def test_invalid_email(self):
        """Test invalid email format fails validation."""
        form = COBApplicantForm({
            'entity_type': 'fizicko',
            'ime': 'Marko',
            'prezime': 'Petrović',
            'adresa': 'Beograd',
            'email': 'not-an-email',  # Invalid
            'telefon': '0651234568',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_invalid_phone(self):
        """Test invalid phone format fails validation."""
        form = COBApplicantForm({
            'entity_type': 'fizicko',
            'ime': 'Marko',
            'prezime': 'Petrović',
            'adresa': 'Beograd',
            'email': 'marko@example.com',
            'telefon': '123',  # Invalid
        })
        self.assertFalse(form.is_valid())
        self.assertIn('telefon', form.errors)

    def test_phone_normalization(self):
        """Test phone number normalization (06X → +3816X)."""
        form = COBApplicantForm({
            'entity_type': 'fizicko',
            'ime': 'Marko',
            'prezime': 'Petrović',
            'adresa': 'Beograd',
            'email': 'marko@example.com',
            'telefon': '0651234568',
        })
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['telefon'], '+381651234568')  # ISSUE 2 FIX: 8 digits

    def test_serbian_characters(self):
        """Test Serbian characters (č, ć, š, đ, ž) are accepted."""
        form = COBApplicantForm({
            'entity_type': 'fizicko',
            'ime': 'Đorđe',
            'prezime': 'Đurić',
            'adresa': 'Niš, Šumadijska 25',
            'email': 'djordje@example.com',
            'telefon': '0651234568',
        })
        self.assertTrue(form.is_valid())

    def test_no_jmbg_field(self):
        """Test COB form does NOT have JMBG field (simplification)."""
        form = COBApplicantForm()
        self.assertNotIn('jmbg', form.fields)

    def test_no_maticni_broj_field(self):
        """Test COB form does NOT have matični broj field (simplification)."""
        form = COBApplicantForm()
        self.assertNotIn('maticni_broj', form.fields)

    def test_max_length_ime(self):
        """Test ime max length validation (100 chars)."""
        form = COBApplicantForm({
            'entity_type': 'fizicko',
            'ime': 'A' * 150,  # Exceeds max
            'prezime': 'Petrović',
            'adresa': 'Beograd',
            'email': 'test@example.com',
            'telefon': '0651234568',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('ime', form.errors)

    def test_max_length_prezime(self):
        """Test prezime max length validation (100 chars)."""
        form = COBApplicantForm({
            'entity_type': 'fizicko',
            'ime': 'Marko',
            'prezime': 'A' * 150,  # Exceeds max
            'adresa': 'Beograd',
            'email': 'test@example.com',
            'telefon': '0651234568',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('prezime', form.errors)

    def test_max_length_naziv_organizacije(self):
        """Test naziv_organizacije max length validation (200 chars)."""
        form = COBApplicantForm({
            'entity_type': 'pravno',
            'naziv_organizacije': 'A' * 250,  # Exceeds max
            'adresa': 'Novi Sad',
            'email': 'test@example.com',
            'telefon': '0651234568',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('naziv_organizacije', form.errors)

    def test_max_length_adresa(self):
        """Test adresa max length validation (300 chars)."""
        form = COBApplicantForm({
            'entity_type': 'fizicko',
            'ime': 'Marko',
            'prezime': 'Petrović',
            'adresa': 'A' * 350,  # Exceeds max
            'email': 'test@example.com',
            'telefon': '0651234568',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('adresa', form.errors)

    def test_missing_entity_type(self):
        """Test missing entity_type fails validation."""
        form = COBApplicantForm({
            'ime': 'Marko',
            'prezime': 'Petrović',
            'adresa': 'Beograd',
            'email': 'test@example.com',
            'telefon': '0651234568',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('entity_type', form.errors)

    def test_invalid_entity_type(self):
        """Test invalid entity_type value fails validation."""
        form = COBApplicantForm({
            'entity_type': 'invalid',
            'ime': 'Marko',
            'prezime': 'Petrović',
            'adresa': 'Beograd',
            'email': 'test@example.com',
            'telefon': '0651234568',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('entity_type', form.errors)

    def test_missing_adresa(self):
        """Test missing adresa fails validation."""
        form = COBApplicantForm({
            'entity_type': 'fizicko',
            'ime': 'Marko',
            'prezime': 'Petrović',
            'adresa': '',  # Missing
            'email': 'test@example.com',
            'telefon': '0651234568',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('adresa', form.errors)

    def test_missing_email(self):
        """Test missing email fails validation."""
        form = COBApplicantForm({
            'entity_type': 'fizicko',
            'ime': 'Marko',
            'prezime': 'Petrović',
            'adresa': 'Beograd',
            'email': '',  # Missing
            'telefon': '0651234568',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_missing_telefon(self):
        """Test missing telefon fails validation."""
        form = COBApplicantForm({
            'entity_type': 'fizicko',
            'ime': 'Marko',
            'prezime': 'Petrović',
            'adresa': 'Beograd',
            'email': 'test@example.com',
            'telefon': '',  # Missing
        })
        self.assertFalse(form.is_valid())
        self.assertIn('telefon', form.errors)

    def test_phone_normalization_already_normalized(self):
        """Test phone number already in +381 format remains unchanged."""
        form = COBApplicantForm({
            'entity_type': 'fizicko',
            'ime': 'Marko',
            'prezime': 'Petrović',
            'adresa': 'Beograd',
            'email': 'marko@example.com',
            'telefon': '+381651234568',
        })
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['telefon'], '+381651234568')  # ISSUE 2 FIX: 8 digits

    def test_whitespace_only_ime(self):
        """Test whitespace-only ime fails validation (ISSUE 12 FIX)."""
        form = COBApplicantForm({
            'entity_type': 'fizicko',
            'ime': '   ',  # Whitespace only
            'prezime': 'Petrović',
            'adresa': 'Beograd',
            'email': 'test@example.com',
            'telefon': '0651234568',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('ime', form.errors)

    def test_whitespace_only_naziv_organizacije(self):
        """Test whitespace-only naziv_organizacije fails validation (ISSUE 12 FIX)."""
        form = COBApplicantForm({
            'entity_type': 'pravno',
            'naziv_organizacije': '   ',  # Whitespace only
            'adresa': 'Novi Sad',
            'email': 'test@example.com',
            'telefon': '0651234568',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('naziv_organizacije', form.errors)
