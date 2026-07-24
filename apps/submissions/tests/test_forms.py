# -*- coding: utf-8 -*-
"""
Unit tests for Django Forms.
Story 3.2: COBApplicantForm - Simplified applicant validation (no JMBG/matični broj)
Story 3.3: COBInitiativeDataForm - Initiative data validation (no budget)
Story 3.4: COBSectionIIIForm - Simplified documentation validation (2 files only)
"""
from django.test import TestCase
from apps.submissions.forms import COBApplicantForm, COBInitiativeDataForm, COBSectionIIIForm, validate_cob_file_metadata


class COBApplicantFormTests(TestCase):
    """Test suite for COBApplicantForm validation."""

    def test_valid_fizicko_lice(self):
        """Test valid fizičko lice data passes validation."""
        form = COBApplicantForm({
            'entity_type': 'fizicko',
            'ime': 'Marko',
            'prezime': 'Petrović',
            'id_broj': 'ID1234567',  # Story 5.1: Required for fizičko lice (ID + 7 digits)
            'adresa': 'Beograd, Kneza Miloša 10',
            'email': 'marko@example.com',
            'telefon': '0651234568',  # Story 5.4+: 6+ digits, no letters
        })
        self.assertTrue(form.is_valid())

    def test_valid_pravno_lice(self):
        """Test valid pravno lice data passes validation."""
        form = COBApplicantForm({
            'entity_type': 'pravno',
            'naziv_organizacije': 'Udruženje građana Domovik',
            'registracioni_broj': 'REG-2024-ABC',  # Story 5.1: Required for pravno lice
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

    def test_phone_valid_10_digits(self):
        """Test 10-digit phone passes validation (Story 5.4+: 6+ digits, no normalization)."""
        form = COBApplicantForm({
            'entity_type': 'fizicko',
            'ime': 'Marko',
            'prezime': 'Petrović',
            'id_broj': 'ID1234567',  # Story 5.1: Required for fizičko lice (ID + 7 digits)
            'adresa': 'Beograd',
            'email': 'marko@example.com',
            'telefon': '0651234568',  # 10 digits
        })
        self.assertTrue(form.is_valid())
        # Story 5.4+: No normalization, phone stays as entered
        self.assertEqual(form.cleaned_data['telefon'], '0651234568')

    def test_phone_valid_9_digits(self):
        """Test 9-digit phone passes validation (Story 5.4+: 6+ digits)."""
        form = COBApplicantForm({
            'entity_type': 'fizicko',
            'ime': 'Marko',
            'prezime': 'Petrović',
            'id_broj': 'ID1234567',  # Story 5.1: Required for fizičko lice (ID + 7 digits)
            'adresa': 'Beograd',
            'email': 'marko@example.com',
            'telefon': '065123456',  # 9 digits
        })
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['telefon'], '065123456')

    def test_serbian_characters(self):
        """Test Serbian characters (č, ć, š, đ, ž) are accepted."""
        form = COBApplicantForm({
            'entity_type': 'fizicko',
            'ime': 'Đorđe',
            'prezime': 'Đurić',
            'id_broj': 'ID1234567',  # Story 5.1: Required for fizičko lice (ID + 7 digits)
            'adresa': 'Niš, Šumadijska 25',
            'email': 'djordje@example.com',
            'telefon': '0651234568',
        })
        self.assertTrue(form.is_valid())

    def test_no_jmbg_field(self):
        """Test COB form does NOT have JMBG field (uses id_broj instead - Story 5.1)."""
        form = COBApplicantForm()
        self.assertNotIn('jmbg', form.fields)

    def test_no_maticni_broj_field(self):
        """Test COB form does NOT have matični broj field (uses registracioni_broj instead - Story 5.1)."""
        form = COBApplicantForm()
        self.assertNotIn('maticni_broj', form.fields)

    def test_no_id_broj_field(self):
        """Z3 (2026-07-24): COB form no longer has id_broj (Broj lične karte) field."""
        form = COBApplicantForm()
        self.assertNotIn('id_broj', form.fields)

    def test_has_registracioni_broj_field(self):
        """Test COB form HAS registracioni_broj field (Story 5.1)."""
        form = COBApplicantForm()
        self.assertIn('registracioni_broj', form.fields)

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

    def test_phone_with_plus_prefix(self):
        """Test phone with +381 prefix passes validation (Story 5.4+: 6+ digits)."""
        form = COBApplicantForm({
            'entity_type': 'fizicko',
            'ime': 'Marko',
            'prezime': 'Petrović',
            'id_broj': 'ID1234567',  # Story 5.1: Required for fizičko lice (ID + 7 digits)
            'adresa': 'Beograd',
            'email': 'marko@example.com',
            'telefon': '+381651234568',  # Valid: 12 digits after removing +
        })
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['telefon'], '+381651234568')

    def test_phone_valid_6_digits_minimum(self):
        """Test 6-digit phone passes validation (Story 5.4+: minimum 6 digits)."""
        form = COBApplicantForm({
            'entity_type': 'fizicko',
            'ime': 'Marko',
            'prezime': 'Petrović',
            'id_broj': 'ID1234567',  # Story 5.1: Required for fizičko lice (ID + 7 digits)
            'adresa': 'Beograd',
            'email': 'marko@example.com',
            'telefon': '123456',  # Exactly 6 digits (minimum)
        })
        self.assertTrue(form.is_valid())

    def test_phone_too_short_5_digits(self):
        """Test 5-digit phone (too short) fails validation (Story 5.4+: minimum 6)."""
        form = COBApplicantForm({
            'entity_type': 'fizicko',
            'ime': 'Marko',
            'prezime': 'Petrović',
            'adresa': 'Beograd',
            'email': 'marko@example.com',
            'telefon': '12345',  # Only 5 digits (too short)
        })
        self.assertFalse(form.is_valid())
        self.assertIn('telefon', form.errors)

    def test_phone_with_letters_fails(self):
        """Test phone with letters fails validation (Story 5.4+: no letters)."""
        form = COBApplicantForm({
            'entity_type': 'fizicko',
            'ime': 'Marko',
            'prezime': 'Petrović',
            'adresa': 'Beograd',
            'email': 'marko@example.com',
            'telefon': '065ABC1234',  # Contains letters
        })
        self.assertFalse(form.is_valid())
        self.assertIn('telefon', form.errors)

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


class COBInitiativeDataFormTests(TestCase):
    """Test suite for COBInitiativeDataForm validation."""

    def test_valid_initiative_data(self):
        """Test valid initiative data passes validation."""
        form = COBInitiativeDataForm({
            'naslov': 'Inicijativa za park',
            'kratak_opis': 'Obnova lokalnog parka sa igralištima.',
            'problem': 'Park je zanemaren i nebezbedno mesto za decu.',
            'cilj': 'Kreirati bezbednu zelenu površinu za zajednicu.',
            'planirani_koraci': 'Prikupljanje sredstava, čišćenje, postavljanje opreme.',
            'ocekivani_uticaj': 'Povećanje kvaliteta života residents i dečije bezbednosti.',
        })
        self.assertTrue(form.is_valid())

    def test_missing_required_fields(self):
        """Test missing required fields fail validation."""
        form = COBInitiativeDataForm({
            'naslov': '',  # Missing
            'kratak_opis': 'Opis',
            'problem': 'Problem',
            'cilj': 'Cilj',
            'planirani_koraci': 'Koraci',
            'ocekivani_uticaj': 'Uticaj',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('naslov', form.errors)

    def test_naslov_max_length(self):
        """Test naslov exceeding 150 characters fails validation."""
        form = COBInitiativeDataForm({
            'naslov': 'A' * 200,  # Exceeds 150
            'kratak_opis': 'Opis',
            'problem': 'Problem',
            'cilj': 'Cilj',
            'planirani_koraci': 'Koraci',
            'ocekivani_uticaj': 'Uticaj',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('naslov', form.errors)

    def test_kratak_opis_max_length(self):
        """Test kratak_opis exceeding 500 characters fails validation."""
        form = COBInitiativeDataForm({
            'naslov': 'Naslov',
            'kratak_opis': 'A' * 600,  # Exceeds 500
            'problem': 'Problem',
            'cilj': 'Cilj',
            'planirani_koraci': 'Koraci',
            'ocekivani_uticaj': 'Uticaj',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('kratak_opis', form.errors)

    def test_problem_max_length(self):
        """Test problem exceeding 1500 characters fails validation."""
        form = COBInitiativeDataForm({
            'naslov': 'Naslov',
            'kratak_opis': 'Opis',
            'problem': 'A' * 1600,  # Exceeds 1500
            'cilj': 'Cilj',
            'planirani_koraci': 'Koraci',
            'ocekivani_uticaj': 'Uticaj',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('problem', form.errors)

    def test_cilj_max_length(self):
        """Test cilj exceeding 1500 characters fails validation (ISSUE 9 FIX)."""
        form = COBInitiativeDataForm({
            'naslov': 'Naslov',
            'kratak_opis': 'Opis',
            'problem': 'Problem',
            'cilj': 'A' * 1600,  # Exceeds 1500
            'planirani_koraci': 'Koraci',
            'ocekivani_uticaj': 'Uticaj',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('cilj', form.errors)

    def test_planirani_koraci_max_length(self):
        """Test planirani_koraci exceeding 1500 characters fails validation (ISSUE 9 FIX)."""
        form = COBInitiativeDataForm({
            'naslov': 'Naslov',
            'kratak_opis': 'Opis',
            'problem': 'Problem',
            'cilj': 'Cilj',
            'planirani_koraci': 'A' * 1600,  # Exceeds 1500
            'ocekivani_uticaj': 'Uticaj',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('planirani_koraci', form.errors)

    def test_ocekivani_uticaj_max_length(self):
        """Test ocekivani_uticaj exceeding 1500 characters fails validation (ISSUE 9 FIX)."""
        form = COBInitiativeDataForm({
            'naslov': 'Naslov',
            'kratak_opis': 'Opis',
            'problem': 'Problem',
            'cilj': 'Cilj',
            'planirani_koraci': 'Koraci',
            'ocekivani_uticaj': 'A' * 1600,  # Exceeds 1500
        })
        self.assertFalse(form.is_valid())
        self.assertIn('ocekivani_uticaj', form.errors)

    def test_whitespace_only_naslov(self):
        """Test naslov with only whitespace fails validation."""
        form = COBInitiativeDataForm({
            'naslov': '    ',  # Whitespace only
            'kratak_opis': 'Opis',
            'problem': 'Problem',
            'cilj': 'Cilj',
            'planirani_koraci': 'Koraci',
            'ocekivani_uticaj': 'Uticaj',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('naslov', form.errors)

    def test_whitespace_only_problem(self):
        """Test problem with only whitespace fails validation."""
        form = COBInitiativeDataForm({
            'naslov': 'Naslov',
            'kratak_opis': 'Opis',
            'problem': '    ',  # Whitespace only
            'cilj': 'Cilj',
            'planirani_koraci': 'Koraci',
            'ocekivani_uticaj': 'Uticaj',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('problem', form.errors)

    def test_whitespace_only_kratak_opis(self):
        """Test kratak_opis with only whitespace fails validation (ISSUE 10 FIX)."""
        form = COBInitiativeDataForm({
            'naslov': 'Naslov',
            'kratak_opis': '    ',  # Whitespace only
            'problem': 'Problem',
            'cilj': 'Cilj',
            'planirani_koraci': 'Koraci',
            'ocekivani_uticaj': 'Uticaj',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('kratak_opis', form.errors)

    def test_whitespace_only_cilj(self):
        """Test cilj with only whitespace fails validation (ISSUE 10 FIX)."""
        form = COBInitiativeDataForm({
            'naslov': 'Naslov',
            'kratak_opis': 'Opis',
            'problem': 'Problem',
            'cilj': '    ',  # Whitespace only
            'planirani_koraci': 'Koraci',
            'ocekivani_uticaj': 'Uticaj',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('cilj', form.errors)

    def test_whitespace_only_planirani_koraci(self):
        """Test planirani_koraci with only whitespace fails validation (ISSUE 10 FIX)."""
        form = COBInitiativeDataForm({
            'naslov': 'Naslov',
            'kratak_opis': 'Opis',
            'problem': 'Problem',
            'cilj': 'Cilj',
            'planirani_koraci': '    ',  # Whitespace only
            'ocekivani_uticaj': 'Uticaj',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('planirani_koraci', form.errors)

    def test_whitespace_only_ocekivani_uticaj(self):
        """Test ocekivani_uticaj with only whitespace fails validation (ISSUE 10 FIX)."""
        form = COBInitiativeDataForm({
            'naslov': 'Naslov',
            'kratak_opis': 'Opis',
            'problem': 'Problem',
            'cilj': 'Cilj',
            'planirani_koraci': 'Koraci',
            'ocekivani_uticaj': '    ',  # Whitespace only
        })
        self.assertFalse(form.is_valid())
        self.assertIn('ocekivani_uticaj', form.errors)

    def test_serbian_characters(self):
        """Test Serbian characters (č, ć, š, đ, ž) are accepted."""
        form = COBInitiativeDataForm({
            'naslov': 'Иницијатива за заједницу',
            'kratak_opis': 'Побољшање квалитета живота',
            'problem': 'Недостатак зелених површина',
            'cilj': 'Креирати заједнички простор',
            'planirani_koraci': 'Организација волонтера',
            'ocekivani_uticaj': 'Јачање заједничког духа',
        })
        self.assertTrue(form.is_valid())

    def test_leading_trailing_whitespace_normalization(self):
        """Test leading/trailing whitespace is stripped."""
        form = COBInitiativeDataForm({
            'naslov': '  Test inicijativa  ',
            'kratak_opis': '  Kratak opis  ',
            'problem': '  Problem  ',
            'cilj': '  Cilj  ',
            'planirani_koraci': '  Koraci  ',
            'ocekivani_uticaj': '  Uticaj  ',
        })
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['naslov'], 'Test inicijativa')
        self.assertEqual(form.cleaned_data['kratak_opis'], 'Kratak opis')

    def test_all_fields_at_max_length(self):
        """Test all fields at exactly max length pass validation."""
        form = COBInitiativeDataForm({
            'naslov': 'A' * 150,
            'kratak_opis': 'B' * 500,
            'problem': 'C' * 1500,
            'cilj': 'D' * 1500,
            'planirani_koraci': 'E' * 1500,
            'ocekivani_uticaj': 'F' * 1500,
        })
        self.assertTrue(form.is_valid())

    def test_no_budzet_field(self):
        """Test COB form does NOT have budžet field (simplification)."""
        form = COBInitiativeDataForm()
        self.assertNotIn('budzet', form.fields)
        self.assertNotIn('totalni_budzet', form.fields)

    def test_no_ciljne_grupe_field(self):
        """Test COB form does NOT have ciljne_grupe field (simplification)."""
        form = COBInitiativeDataForm()
        self.assertNotIn('ciljne_grupe', form.fields)

    def test_no_aktivnosti_field(self):
        """Test COB form does NOT have aktivnosti field (simplification)."""
        form = COBInitiativeDataForm()
        self.assertNotIn('aktivnosti', form.fields)

    def test_no_rezultati_field(self):
        """Test COB form does NOT have rezultati field (simplification)."""
        form = COBInitiativeDataForm()
        self.assertNotIn('rezultati', form.fields)


class COBSectionIIIFormTests(TestCase):
    """Test suite for COBSectionIIIForm validation (Story 3.4)."""

    def test_valid_section_iii_data(self):
        """Test valid Section III data passes validation."""
        form = COBSectionIIIForm({
            'saglasnost_gdpr': True,
        })
        self.assertTrue(form.is_valid())

    def test_missing_gdpr_consent(self):
        """Test missing GDPR consent fails validation."""
        form = COBSectionIIIForm({
            'saglasnost_gdpr': False,
        })
        self.assertFalse(form.is_valid())
        self.assertIn('saglasnost_gdpr', form.errors)

    # Story 5.4: Updated tests for new COB file categories
    # BUDZET_INICIJATIVE (required, XLS/XLSX) and PISMO_PODRSKE (optional, PDF/DOC/DOCX)

    def test_valid_file_metadata_with_both_files(self):
        """Test valid file metadata with both files passes validation."""
        file_metadata = {
            'BUDZET_INICIJATIVE': [{'name': 'budget.xlsx', 'size': 1024000}],
            'PISMO_PODRSKE': [{'name': 'pismo.pdf', 'size': 512000}],
        }
        valid, errors = validate_cob_file_metadata(file_metadata)
        self.assertTrue(valid)
        self.assertEqual(errors, {})

    def test_valid_file_metadata_budget_only(self):
        """Story 5.4: Test valid metadata with only required budget file passes."""
        file_metadata = {
            'BUDZET_INICIJATIVE': [{'name': 'budget.xlsx', 'size': 1024000}],
            # PISMO_PODRSKE is optional - not provided
        }
        valid, errors = validate_cob_file_metadata(file_metadata)
        self.assertTrue(valid)
        self.assertEqual(errors, {})

    def test_missing_budzet_inicijative(self):
        """Story 5.4: Test missing BUDZET_INICIJATIVE fails validation."""
        file_metadata = {
            'PISMO_PODRSKE': [{'name': 'pismo.pdf', 'size': 512000}],
        }
        valid, errors = validate_cob_file_metadata(file_metadata)
        self.assertFalse(valid)
        self.assertIn('BUDZET_INICIJATIVE', errors)

    def test_pismo_podrske_is_optional(self):
        """Story 5.4: Test missing PISMO_PODRSKE does NOT fail validation (it's optional)."""
        file_metadata = {
            'BUDZET_INICIJATIVE': [{'name': 'budget.xlsx', 'size': 1024000}],
        }
        valid, errors = validate_cob_file_metadata(file_metadata)
        self.assertTrue(valid)  # Should pass - pismo is optional

    def test_empty_file_list_budzet(self):
        """Test empty file list for budget fails validation."""
        file_metadata = {
            'BUDZET_INICIJATIVE': [],
            'PISMO_PODRSKE': [{'name': 'pismo.pdf', 'size': 512000}],
        }
        valid, errors = validate_cob_file_metadata(file_metadata)
        self.assertFalse(valid)
        self.assertIn('BUDZET_INICIJATIVE', errors)

    def test_multiple_files_budzet_category(self):
        """Test multiple files in budget category fails validation."""
        file_metadata = {
            'BUDZET_INICIJATIVE': [
                {'name': 'budget1.xlsx', 'size': 1024},
                {'name': 'budget2.xlsx', 'size': 2048},
            ],
        }
        valid, errors = validate_cob_file_metadata(file_metadata)
        self.assertFalse(valid)
        self.assertIn('BUDZET_INICIJATIVE', errors)

    def test_invalid_file_metadata_structure(self):
        """Test invalid file metadata structure fails validation."""
        file_metadata = 'not a dict'
        valid, errors = validate_cob_file_metadata(file_metadata)
        self.assertFalse(valid)
        self.assertIn('__all__', errors)

    def test_unexpected_file_categories(self):
        """Test unexpected file categories (COA categories) fail validation."""
        file_metadata = {
            'BUDZET_INICIJATIVE': [{'name': 'budget.xlsx', 'size': 1024000}],
            'BUDGET': [{'name': 'budget.xlsx', 'size': 2048}],  # Invalid for COB
            'BIOGRAPHY': [{'name': 'bio.pdf', 'size': 1024}],  # Invalid for COB
        }
        valid, errors = validate_cob_file_metadata(file_metadata)
        self.assertFalse(valid)
        self.assertIn('__all__', errors)

    def test_file_metadata_non_list_value(self):
        """Test file metadata with non-list value fails validation."""
        file_metadata = {
            'BUDZET_INICIJATIVE': 'not a list',
        }
        valid, errors = validate_cob_file_metadata(file_metadata)
        self.assertFalse(valid)
        self.assertIn('BUDZET_INICIJATIVE', errors)

    # Story 5.4: Test for empty string file names
    def test_empty_string_filename(self):
        """Test file with empty string name fails validation."""
        file_metadata = {
            'BUDZET_INICIJATIVE': [{'name': '', 'size': 1024000}],
        }
        valid, errors = validate_cob_file_metadata(file_metadata)
        self.assertFalse(valid)
        self.assertIn('BUDZET_INICIJATIVE', errors)
        self.assertEqual(errors['BUDZET_INICIJATIVE'][0]['code'], 'empty_filename')

    def test_whitespace_only_filename(self):
        """Test file with whitespace-only name fails validation."""
        file_metadata = {
            'BUDZET_INICIJATIVE': [{'name': '   ', 'size': 1024000}],
        }
        valid, errors = validate_cob_file_metadata(file_metadata)
        self.assertFalse(valid)
        self.assertIn('BUDZET_INICIJATIVE', errors)
        self.assertEqual(errors['BUDZET_INICIJATIVE'][0]['code'], 'empty_filename')

    # Test for missing 'name' or 'size' fields
    def test_missing_name_field(self):
        """Test file object missing 'name' field fails validation."""
        file_metadata = {
            'BUDZET_INICIJATIVE': [{'size': 1024000}],  # Missing 'name'
        }
        valid, errors = validate_cob_file_metadata(file_metadata)
        self.assertFalse(valid)
        self.assertIn('BUDZET_INICIJATIVE', errors)
        self.assertEqual(errors['BUDZET_INICIJATIVE'][0]['code'], 'missing_name')

    def test_missing_size_field(self):
        """Test file object missing 'size' field fails validation."""
        file_metadata = {
            'BUDZET_INICIJATIVE': [{'name': 'budget.xlsx'}],  # Missing 'size'
        }
        valid, errors = validate_cob_file_metadata(file_metadata)
        self.assertFalse(valid)
        self.assertIn('BUDZET_INICIJATIVE', errors)
        self.assertEqual(errors['BUDZET_INICIJATIVE'][0]['code'], 'missing_size')

    def test_missing_both_name_and_size_fields(self):
        """Test file object missing both 'name' and 'size' fields fails validation."""
        file_metadata = {
            'BUDZET_INICIJATIVE': [{}],  # Missing both fields
        }
        valid, errors = validate_cob_file_metadata(file_metadata)
        self.assertFalse(valid)
        self.assertIn('BUDZET_INICIJATIVE', errors)
        self.assertEqual(errors['BUDZET_INICIJATIVE'][0]['code'], 'missing_name')

    # Story 5.4: Test for BUDZET_INICIJATIVE requires XLS/XLSX format
    def test_budzet_invalid_extension_pdf(self):
        """Story 5.4: Test budget with .pdf extension fails validation (requires XLS/XLSX)."""
        file_metadata = {
            'BUDZET_INICIJATIVE': [{'name': 'budget.pdf', 'size': 1024000}],
        }
        valid, errors = validate_cob_file_metadata(file_metadata)
        self.assertFalse(valid)
        self.assertIn('BUDZET_INICIJATIVE', errors)
        self.assertEqual(errors['BUDZET_INICIJATIVE'][0]['code'], 'invalid_extension')

    def test_budzet_invalid_extension_docx(self):
        """Story 5.4: Test budget with .docx extension fails validation (requires XLS/XLSX)."""
        file_metadata = {
            'BUDZET_INICIJATIVE': [{'name': 'budget.docx', 'size': 1024000}],
        }
        valid, errors = validate_cob_file_metadata(file_metadata)
        self.assertFalse(valid)
        self.assertIn('BUDZET_INICIJATIVE', errors)
        self.assertEqual(errors['BUDZET_INICIJATIVE'][0]['code'], 'invalid_extension')

    def test_budzet_valid_extension_xls(self):
        """Story 5.4: Test budget with .xls extension passes validation."""
        file_metadata = {
            'BUDZET_INICIJATIVE': [{'name': 'budget.xls', 'size': 1024000}],
        }
        valid, errors = validate_cob_file_metadata(file_metadata)
        self.assertTrue(valid)
        self.assertEqual(errors, {})

    def test_budzet_valid_extension_xlsx(self):
        """Story 5.4: Test budget with .xlsx extension passes validation."""
        file_metadata = {
            'BUDZET_INICIJATIVE': [{'name': 'budget.xlsx', 'size': 1024000}],
        }
        valid, errors = validate_cob_file_metadata(file_metadata)
        self.assertTrue(valid)
        self.assertEqual(errors, {})

    # Story 5.4: Test for PISMO_PODRSKE requires PDF/DOC/DOCX format
    def test_pismo_invalid_extension_xlsx(self):
        """Story 5.4: Test support letter with .xlsx extension fails validation."""
        file_metadata = {
            'BUDZET_INICIJATIVE': [{'name': 'budget.xlsx', 'size': 1024000}],
            'PISMO_PODRSKE': [{'name': 'pismo.xlsx', 'size': 512000}],
        }
        valid, errors = validate_cob_file_metadata(file_metadata)
        self.assertFalse(valid)
        self.assertIn('PISMO_PODRSKE', errors)
        self.assertEqual(errors['PISMO_PODRSKE'][0]['code'], 'invalid_extension')

    def test_pismo_valid_extension_pdf(self):
        """Story 5.4: Test support letter with .pdf extension passes validation."""
        file_metadata = {
            'BUDZET_INICIJATIVE': [{'name': 'budget.xlsx', 'size': 1024000}],
            'PISMO_PODRSKE': [{'name': 'pismo.pdf', 'size': 512000}],
        }
        valid, errors = validate_cob_file_metadata(file_metadata)
        self.assertTrue(valid)
        self.assertEqual(errors, {})

    def test_pismo_valid_extension_doc(self):
        """Story 5.4: Test support letter with .doc extension passes validation."""
        file_metadata = {
            'BUDZET_INICIJATIVE': [{'name': 'budget.xlsx', 'size': 1024000}],
            'PISMO_PODRSKE': [{'name': 'pismo.doc', 'size': 512000}],
        }
        valid, errors = validate_cob_file_metadata(file_metadata)
        self.assertTrue(valid)
        self.assertEqual(errors, {})

    def test_no_extension(self):
        """Test file with no extension fails validation."""
        file_metadata = {
            'BUDZET_INICIJATIVE': [{'name': 'document', 'size': 1024000}],
        }
        valid, errors = validate_cob_file_metadata(file_metadata)
        self.assertFalse(valid)
        self.assertIn('BUDZET_INICIJATIVE', errors)
        self.assertEqual(errors['BUDZET_INICIJATIVE'][0]['code'], 'invalid_extension')

    def test_valid_extensions_case_insensitive(self):
        """Test valid extensions with different cases pass validation."""
        file_metadata = {
            'BUDZET_INICIJATIVE': [{'name': 'budget.XLSX', 'size': 1024000}],
            'PISMO_PODRSKE': [{'name': 'pismo.DOC', 'size': 512000}],
        }
        valid, errors = validate_cob_file_metadata(file_metadata)
        self.assertTrue(valid)
        self.assertEqual(errors, {})

    # Test for file size exceeding 10MB
    def test_file_size_exceeds_10mb(self):
        """Test file exceeding 10MB (10485760 bytes) fails validation."""
        file_metadata = {
            'BUDZET_INICIJATIVE': [{'name': 'budget.xlsx', 'size': 10485761}],  # 10MB + 1 byte
        }
        valid, errors = validate_cob_file_metadata(file_metadata)
        self.assertFalse(valid)
        self.assertIn('BUDZET_INICIJATIVE', errors)
        self.assertEqual(errors['BUDZET_INICIJATIVE'][0]['code'], 'file_too_large')

    def test_file_size_exactly_10mb(self):
        """Test file exactly 10MB (10485760 bytes) passes validation."""
        file_metadata = {
            'BUDZET_INICIJATIVE': [{'name': 'budget.xlsx', 'size': 10485760}],  # Exactly 10MB
        }
        valid, errors = validate_cob_file_metadata(file_metadata)
        self.assertTrue(valid)
        self.assertEqual(errors, {})

    def test_file_size_zero(self):
        """Test file with zero size fails validation."""
        file_metadata = {
            'BUDZET_INICIJATIVE': [{'name': 'budget.xlsx', 'size': 0}],
        }
        valid, errors = validate_cob_file_metadata(file_metadata)
        self.assertFalse(valid)
        self.assertIn('BUDZET_INICIJATIVE', errors)
        self.assertEqual(errors['BUDZET_INICIJATIVE'][0]['code'], 'invalid_size')

    def test_file_size_negative(self):
        """Test file with negative size fails validation."""
        file_metadata = {
            'BUDZET_INICIJATIVE': [{'name': 'budget.xlsx', 'size': -1024}],
        }
        valid, errors = validate_cob_file_metadata(file_metadata)
        self.assertFalse(valid)
        self.assertIn('BUDZET_INICIJATIVE', errors)
        self.assertEqual(errors['BUDZET_INICIJATIVE'][0]['code'], 'invalid_size')

    def test_file_size_invalid_format(self):
        """Test file with invalid size format fails validation."""
        file_metadata = {
            'BUDZET_INICIJATIVE': [{'name': 'budget.xlsx', 'size': 'not_a_number'}],
        }
        valid, errors = validate_cob_file_metadata(file_metadata)
        self.assertFalse(valid)
        self.assertIn('BUDZET_INICIJATIVE', errors)
        self.assertEqual(errors['BUDZET_INICIJATIVE'][0]['code'], 'invalid_size_format')

    # Test for case-sensitive category names
    def test_lowercase_category_name(self):
        """Test lowercase category name fails validation."""
        file_metadata = {
            'budzet_inicijative': [{'name': 'budget.xlsx', 'size': 1024000}],  # Lowercase
        }
        valid, errors = validate_cob_file_metadata(file_metadata)
        self.assertFalse(valid)
        self.assertIn('BUDZET_INICIJATIVE', errors)
        self.assertIn('__all__', errors)

    def test_mixed_case_category_name(self):
        """Test mixed case category name fails validation."""
        file_metadata = {
            'BUDZET_INICIJATIVE': [{'name': 'budget.xlsx', 'size': 1024000}],
            'Pismo_Podrske': [{'name': 'pismo.pdf', 'size': 512000}],  # Mixed case
        }
        valid, errors = validate_cob_file_metadata(file_metadata)
        self.assertFalse(valid)
        self.assertIn('__all__', errors)

    # Test for multiple files in optional category
    def test_multiple_files_pismo_podrske(self):
        """Test multiple files in optional support letter category fails validation."""
        file_metadata = {
            'BUDZET_INICIJATIVE': [{'name': 'budget.xlsx', 'size': 1024000}],
            'PISMO_PODRSKE': [
                {'name': 'pismo1.pdf', 'size': 512},
                {'name': 'pismo2.pdf', 'size': 1024},
            ],
        }
        valid, errors = validate_cob_file_metadata(file_metadata)
        self.assertFalse(valid)
        self.assertIn('PISMO_PODRSKE', errors)
        self.assertEqual(errors['PISMO_PODRSKE'][0]['code'], 'too_many_files')

    # Story 5.4: Test that only budget is required
    def test_only_budget_required_success(self):
        """Story 5.4: Test that only budget file is required for valid submission."""
        file_metadata = {
            'BUDZET_INICIJATIVE': [{'name': 'budget.xlsx', 'size': 1024000}],
        }
        valid, errors = validate_cob_file_metadata(file_metadata)
        self.assertTrue(valid)
        self.assertEqual(errors, {})
