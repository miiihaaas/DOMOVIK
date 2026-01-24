# -*- coding: utf-8 -*-
"""
Django Forms for COA/COB application submission.
Story 2.2: COAFormSectionI - Section I (General Data Entry)
Story 2.8: FileUploadForm - File Upload with Validation
Story 2.11: Updated for ProjectData model separation
Story 3.2: COBApplicantForm - Simplified applicant validation (no JMBG/matični broj)
"""
from typing import Dict, Tuple, Any, List, Optional
import re

from django import forms
from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory
from apps.submissions.models import Applicant, Application, ProjectData, ClanTima
from apps.submissions.validators import (
    validate_file_extension,
    validate_file_size,
    validate_mime_type,
    validate_id_broj,
    validate_registracioni_broj,
    validate_phone,
    validate_phone_optional,
)


# ISSUE 10 FIX: Extract hardcoded category names to constants
# Story 5.4: Updated COB categories - BUDZET_INICIJATIVE (required), PISMO_PODRSKE (optional)
COB_FILE_CATEGORIES_REQUIRED = ['BUDZET_INICIJATIVE']  # Only budget is required
COB_FILE_CATEGORIES_OPTIONAL = ['PISMO_PODRSKE']  # Support letter is optional
COB_FILE_CATEGORIES = COB_FILE_CATEGORIES_REQUIRED + COB_FILE_CATEGORIES_OPTIONAL
ALLOWED_FILE_EXTENSIONS = ['.pdf', '.doc', '.docx']
ALLOWED_EXCEL_EXTENSIONS = ['.xls', '.xlsx']  # Story 5.4: Excel for budget
MAX_FILE_SIZE = 10485760  # 10MB in bytes


class COAFormSectionI(forms.ModelForm):
    """
    COA Form Section I - General Data Entry with Entity Type Switch

    Handles fizičko lice and pravno lice applicant data.
    Leverages Applicant model validation for conditional requirements.
    """

    # Story 5.4+: Unified phone validation - only digits, 6+ chars, no letters
    phone = forms.CharField(
        max_length=20,
        required=True,
        label='Telefon',  # Unified label with COB form
        validators=[validate_phone],
        error_messages={
            'required': 'Telefon je obavezan.',
        },
        help_text='Samo cifre, najmanje 6 cifara',
        widget=forms.TextInput(attrs={'autocomplete': 'tel'})
    )

    class Meta:
        model = Applicant
        fields = [
            'entity_type',
            # Fizičko lice fields
            'first_name', 'last_name', 'jmbg',
            # Pravno lice fields
            'organization_name', 'maticni_broj',
            # Common fields
            'address', 'email', 'phone'
        ]

        widgets = {
            'entity_type': forms.HiddenInput(),  # Handled by JavaScript switcher
            'address': forms.Textarea(attrs={'rows': 3}),
        }

        labels = {
            'entity_type': 'Tip podnosioca',
            'first_name': 'Ime',
            'last_name': 'Prezime',
            # Story 5.1: Changed from "JMBG" to "Broj lične karte / ID broj"
            'jmbg': 'Broj lične karte / ID broj',
            'organization_name': 'Naziv organizacije',
            # Story 5.1: Changed from "Matični broj" to "Registracioni broj"
            'maticni_broj': 'Registracioni broj',
            'address': 'Adresa',
            'email': 'Email adresa',
            'phone': 'Telefon',  # Story 5.4+: Unified label
        }

        help_texts = {
            # Story 5.1: Updated help text for ID broj format
            'jmbg': 'Format: IDxxxxxx (npr. ID123456)',
            'maticni_broj': 'Alfanumerički format (npr. REG-2024-ABC)',
            'email': 'npr. marko@example.com',
            'phone': 'Samo cifre, najmanje 6 cifara',  # Story 5.4+: Updated
        }

    def clean_jmbg(self):
        """
        Validate ID broj (Broj lične karte / ID broj) format.

        Story 5.1: Changed from JMBG (13 digits) to ID broj (IDxxxxxx format)
        """
        jmbg = self.cleaned_data.get('jmbg')
        if jmbg:
            # Normalize: strip whitespace and convert to uppercase
            jmbg = jmbg.strip().upper()
            # Validate format
            validate_id_broj(jmbg)
        return jmbg

    def clean_maticni_broj(self):
        """
        Validate Registracioni broj format.

        Story 5.1: Changed from "Matični broj" (8 digits) to "Registracioni broj" (alphanumeric)
        """
        maticni_broj = self.cleaned_data.get('maticni_broj')
        if maticni_broj:
            # Normalize: strip whitespace
            maticni_broj = maticni_broj.strip()
            # Validate format
            validate_registracioni_broj(maticni_broj)
        return maticni_broj

    def clean(self):
        """
        Conditional validation based on entity_type.

        **CRITICAL - DRY Principle:**
        Leverages existing Applicant.clean() model validation instead of duplicating logic.
        This ensures consistency between form validation and model validation.

        Validation Rules:
        - Fizičko lice: ime + prezime required, ID broj required (COA)
        - Pravno lice: naziv_organizacije required, registracioni broj required (COA)
        """
        cleaned_data = super().clean()

        entity_type = cleaned_data.get('entity_type')

        if entity_type == 'fizicko':
            if not cleaned_data.get('first_name'):
                self.add_error('first_name', 'Ime je obavezno za fizička lica.')
            if not cleaned_data.get('last_name'):
                self.add_error('last_name', 'Prezime je obavezno za fizička lica.')
            # Story 5.1: ID broj is required for fizičko lice (COA)
            if not cleaned_data.get('jmbg'):
                self.add_error('jmbg', 'Broj lične karte / ID broj je obavezan za fizička lica.')
        elif entity_type == 'pravno':
            if not cleaned_data.get('organization_name'):
                self.add_error('organization_name', 'Naziv organizacije je obavezan za pravna lica.')
            # Story 5.1: Registracioni broj is required for pravno lice (COA)
            if not cleaned_data.get('maticni_broj'):
                self.add_error('maticni_broj', 'Registracioni broj je obavezan za pravna lica.')

        return cleaned_data


# Story 5.1: ClanTimaFormSet for team members (dynamic table)
class ClanTimaForm(forms.ModelForm):
    """
    Form for individual team member in the formset.

    Story 5.1: Form Enhancements - Team Members

    All fields are optional per requirements.
    """

    class Meta:
        model = ClanTima
        fields = ['ime_prezime', 'email', 'telefon']
        widgets = {
            'ime_prezime': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ime i prezime',
                'maxlength': '100',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'email@example.com',
            }),
            'telefon': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Samo cifre, min 6 (opciono)',
                'maxlength': '30',
            }),
        }
        labels = {
            'ime_prezime': 'Ime i prezime',
            'email': 'Email',
            'telefon': 'Telefon',
        }

    def clean_telefon(self):
        """
        Validate optional phone number for team members.
        Story 5.4+: Empty OR 6+ digits, no letters.
        """
        telefon = self.cleaned_data.get('telefon')
        if telefon:
            validate_phone_optional(telefon)
        return telefon


# Create the inline formset factory
ClanTimaFormSet = inlineformset_factory(
    Application,
    ClanTima,
    form=ClanTimaForm,
    fields=['ime_prezime', 'email', 'telefon'],
    extra=1,  # Start with 1 empty row
    min_num=1,  # Minimum 1 row
    validate_min=False,  # Don't require the row to be filled
    can_delete=True,  # Allow deletion of rows
    max_num=10,  # Maximum 10 team members
)


class COAFormSectionII(forms.ModelForm):
    """
    COA Form Section II - Project Data Entry with Character Management
    Story 2.6: Section II fields with character limits and budget validation
    Story 2.11: Updated to use ProjectData model
    Story 5.2: Added datum_startovanja, datum_zavrsetka fields + reordered results before activities

    Handles project data including title, short_description, problem, main_goal, etc.
    Client-side character counting managed by character-counter.js.
    Server-side validation ensures data integrity.
    """

    class Meta:
        model = ProjectData
        # Story 5.2: Reordered - results before activities, added date fields
        fields = [
            'title', 'short_description', 'problem', 'main_goal',
            'specific_goals', 'target_groups',
            'results', 'activities',  # Story 5.2: Swapped order
            'datum_startovanja', 'datum_zavrsetka',  # Story 5.2: New date fields
            'total_budget'
        ]

        widgets = {
            'title': forms.Textarea(attrs={'rows': 3}),
            'short_description': forms.Textarea(attrs={'rows': 5}),
            'problem': forms.Textarea(attrs={'rows': 10}),
            'main_goal': forms.Textarea(attrs={'rows': 8}),
            'specific_goals': forms.Textarea(attrs={'rows': 8}),
            'target_groups': forms.Textarea(attrs={'rows': 10}),
            'activities': forms.Textarea(attrs={'rows': 10}),
            'results': forms.Textarea(attrs={'rows': 10}),
            'total_budget': forms.NumberInput(attrs={'step': '1', 'min': '0', 'placeholder': '0'}),
            # Story 5.2: Date picker widgets
            'datum_startovanja': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control date-picker',
            }),
            'datum_zavrsetka': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control date-picker',
            }),
        }

        labels = {
            'title': 'Naslov projekta',
            'short_description': 'Kratak opis',
            'problem': 'Problem koji se rešava',
            'main_goal': 'Glavni cilj',
            'specific_goals': 'Specifični ciljevi',
            'target_groups': 'Ciljne grupe',
            'activities': 'Aktivnosti',
            'results': 'Rezultati',
            'total_budget': 'Totalni budžet (EUR)',
            # Story 5.2: Date field labels
            'datum_startovanja': 'Datum startovanja',
            'datum_zavrsetka': 'Datum završetka',
        }

        help_texts = {
            'title': 'Maksimalno 150 karaktera',
            'short_description': 'Maksimalno 500 karaktera',
            'problem': 'Maksimalno 2000 karaktera',
            'main_goal': 'Maksimalno 1000 karaktera',
            'specific_goals': 'Maksimalno 1000 karaktera',
            'target_groups': 'Maksimalno 1500 karaktera',
            'activities': 'Maksimalno 1500 karaktera',
            'results': 'Maksimalno 1500 karaktera',
            'total_budget': 'Unesite iznos u dinarima (npr. 1000000)',
            # Story 5.2: Date field help texts
            'datum_startovanja': 'Planirani datum početka projekta',
            'datum_zavrsetka': 'Planirani datum završetka projekta',
        }

    def clean_title(self):
        """Validate title field - max 150 characters."""
        title = self.cleaned_data.get('title', '')
        if len(title) > 150:
            raise ValidationError('Naslov ne može biti duži od 150 karaktera.')
        return title

    def clean_short_description(self):
        """Validate short_description field - max 500 characters."""
        short_description = self.cleaned_data.get('short_description', '')
        if len(short_description) > 500:
            raise ValidationError('Opis ne može biti duži od 500 karaktera.')
        return short_description

    def clean_problem(self):
        """Validate problem field - max 2000 characters."""
        problem = self.cleaned_data.get('problem', '')
        if len(problem) > 2000:
            raise ValidationError('Problem ne može biti duži od 2000 karaktera.')
        return problem

    def clean_main_goal(self):
        """Validate main_goal field - max 1000 characters."""
        main_goal = self.cleaned_data.get('main_goal', '')
        if len(main_goal) > 1000:
            raise ValidationError('Glavni cilj ne može biti duži od 1000 karaktera.')
        return main_goal

    def clean_specific_goals(self):
        """Validate specific_goals field - max 1000 characters."""
        specific_goals = self.cleaned_data.get('specific_goals', '')
        if len(specific_goals) > 1000:
            raise ValidationError('Specifični ciljevi ne mogu biti duži od 1000 karaktera.')
        return specific_goals

    def clean_target_groups(self):
        """Validate target_groups field - max 1500 characters."""
        target_groups = self.cleaned_data.get('target_groups', '')
        if len(target_groups) > 1500:
            raise ValidationError('Ciljne grupe ne mogu biti duže od 1500 karaktera.')
        return target_groups

    def clean_activities(self):
        """Validate activities field - max 1500 characters."""
        activities = self.cleaned_data.get('activities', '')
        if len(activities) > 1500:
            raise ValidationError('Aktivnosti ne mogu biti duže od 1500 karaktera.')
        return activities

    def clean_results(self):
        """Validate results field - max 1500 characters."""
        results = self.cleaned_data.get('results', '')
        if len(results) > 1500:
            raise ValidationError('Rezultati ne mogu biti duži od 1500 karaktera.')
        return results

    def clean_total_budget(self):
        """Validate total_budget field - positive number only."""
        total_budget = self.cleaned_data.get('total_budget')
        if total_budget is not None and total_budget < 0:
            raise ValidationError('Budžet mora biti pozitivan broj.')
        return total_budget

    def clean(self):
        """
        Cross-field validation for Section II.

        Story 5.2: Validates that datum_zavrsetka >= datum_startovanja
        """
        cleaned_data = super().clean()

        datum_startovanja = cleaned_data.get('datum_startovanja')
        datum_zavrsetka = cleaned_data.get('datum_zavrsetka')

        # Validate date range if both dates are provided
        if datum_startovanja and datum_zavrsetka:
            if datum_zavrsetka < datum_startovanja:
                self.add_error(
                    'datum_zavrsetka',
                    'Datum završetka ne može biti pre datuma startovanja.'
                )

        return cleaned_data


class FileUploadForm(forms.Form):
    """
    File Upload Form with comprehensive validation.
    Story 2.8: File Upload Infrastructure
    Story 5.4: Updated COB categories (BUDZET_INICIJATIVE, PISMO_PODRSKE)

    Validates:
    - File extension (PDF, DOC, DOCX, XLS, XLSX only)
    - File size (10MB max)
    - MIME type (prevents extension spoofing)
    - File category (budget, biography, support letter, budzet inicijative, pismo podrske)

    Security Features:
    - Extension whitelist enforcement
    - Size limit enforcement
    - MIME type validation
    - CSRF protection (handled by view decorator)
    """

    CATEGORY_CHOICES = [
        # COA categories (Epic 2)
        ('BUDGET', 'Budžet'),
        ('BIOGRAPHY', 'Biografija'),
        ('SUPPORT_LETTER', 'Pismo Podrške'),
        # COB categories (Epic 3, Story 5.4: Updated names)
        ('BUDZET_INICIJATIVE', 'Budžet Inicijative'),
        ('PISMO_PODRSKE', 'Pismo Podrške'),
    ]

    file = forms.FileField(
        label='Fajl',
        help_text='Dozvoljeni formati: PDF, DOC, DOCX, XLS, XLSX (max 10MB)',
        validators=[validate_file_extension, validate_file_size],
        error_messages={
            'required': 'Molimo izaberite fajl za upload.',
            'invalid': 'Upload fajla nije uspeo. Molimo pokušajte ponovo.',
        }
    )

    category = forms.ChoiceField(
        label='Kategorija',
        choices=CATEGORY_CHOICES,
        help_text='Izaberite svrhu upload-ovanog fajla',
        error_messages={
            'required': 'Molimo izaberite kategoriju fajla.',
            'invalid_choice': 'Izabrana kategorija nije validna.',
        }
    )

    def clean_file(self):
        """
        Additional file validation including MIME type check.

        Validates MIME type to prevent extension spoofing attacks.
        """
        file = self.cleaned_data.get('file')

        if file:
            # MIME type validation (prevents .exe renamed to .pdf)
            try:
                validate_mime_type(file)
            except ValidationError as e:
                raise ValidationError(str(e))

        return file


class COBApplicantForm(forms.Form):
    """
    COB (Inicijativa) Section I - Simplified applicant validation.

    Differences from COA:
    - NO jmbg field (fizičko lice)
    - NO maticni_broj field (pravno lice)

    Architecture: Dual-layer validation (client-side + server-side)
    GDPR: Validation only, does NOT persist draft data
    """

    # Entity Type
    entity_type = forms.ChoiceField(
        choices=[
            ('fizicko', 'Fizičko lice'),
            ('pravno', 'Pravno lice'),
        ],
        required=True,
        label='Tip entiteta',  # ISSUE 6 FIX: Add label attribute
        error_messages={
            'required': 'Tip entiteta je obavezan (fizičko ili pravno lice).',
            'invalid_choice': 'Nevalidan tip entiteta. Izaberite fizičko ili pravno lice.',
        }
    )

    # Fizičko lice fields
    ime = forms.CharField(
        max_length=100,
        required=False,  # Conditional based on entity_type
        label='Ime',  # ISSUE 6 FIX: Add label attribute
        error_messages={
            'max_length': 'Ime ne može biti duže od 100 karaktera.',
        },
        widget=forms.TextInput(attrs={'autocomplete': 'given-name'})
    )

    prezime = forms.CharField(
        max_length=100,
        required=False,  # Conditional based on entity_type
        label='Prezime',  # ISSUE 6 FIX: Add label attribute
        error_messages={
            'max_length': 'Prezime ne može biti duže od 100 karaktera.',
        },
        widget=forms.TextInput(attrs={'autocomplete': 'family-name'})
    )

    # Story 5.1: Added ID broj field for fizičko lice (was removed in COB simplification, now required)
    id_broj = forms.CharField(
        max_length=9,
        required=False,  # Conditional based on entity_type
        label='Broj lične karte / ID broj',
        help_text='Format: IDxxxxxx (npr. ID123456)',
        error_messages={
            'max_length': 'ID broj ne može biti duži od 9 karaktera.',
        },
        widget=forms.TextInput(attrs={
            'placeholder': 'ID123456',
            'autocomplete': 'off'
        })
    )

    # Pravno lice fields
    naziv_organizacije = forms.CharField(
        max_length=200,
        required=False,  # Conditional based on entity_type
        label='Naziv organizacije',  # ISSUE 6 FIX: Add label attribute
        error_messages={
            'max_length': 'Naziv organizacije ne može biti duži od 200 karaktera.',
        },
        widget=forms.TextInput(attrs={'autocomplete': 'organization'})
    )

    # Story 5.1: Added registracioni_broj field for pravno lice (was removed in COB simplification, now required)
    registracioni_broj = forms.CharField(
        max_length=50,
        required=False,  # Conditional based on entity_type
        label='Registracioni broj',
        help_text='Alfanumerički format (npr. REG-2024-ABC)',
        error_messages={
            'max_length': 'Registracioni broj ne može biti duži od 50 karaktera.',
        },
        widget=forms.TextInput(attrs={
            'placeholder': 'REG-2024-ABC',
            'autocomplete': 'off'
        })
    )

    # Common fields
    adresa = forms.CharField(
        max_length=300,
        required=True,
        label='Adresa',  # ISSUE 6 FIX: Add label attribute
        error_messages={
            'required': 'Adresa je obavezna.',
            'max_length': 'Adresa ne može biti duža od 300 karaktera.',
        },
        widget=forms.TextInput(attrs={'autocomplete': 'street-address'})
    )

    email = forms.EmailField(
        required=True,
        label='Email adresa',  # ISSUE 6 FIX: Add label attribute
        error_messages={
            'required': 'Email adresa je obavezna.',
            'invalid': 'Neispravan format email adrese. Koristite format: ime@domen.com',
        },
        widget=forms.EmailInput(attrs={'autocomplete': 'email'})
    )

    # Story 5.4+: Unified phone validation - only digits, 6+ chars, no letters
    telefon = forms.CharField(
        max_length=20,
        required=True,
        label='Telefon',
        validators=[validate_phone],
        error_messages={
            'required': 'Telefon je obavezan.',
        },
        help_text='Samo cifre, najmanje 6 cifara',
        widget=forms.TextInput(attrs={'autocomplete': 'tel'})
    )

    def clean(self):
        """
        Custom validation: Entity type conditional logic.

        - If fizičko: ime + prezime required
        - If pravno: naziv_organizacije required
        """
        cleaned_data = super().clean()
        entity_type = cleaned_data.get('entity_type')

        if entity_type == 'fizicko':
            # ISSUE 12 FIX: Validate fizičko lice fields with strip() to catch whitespace-only strings
            ime = cleaned_data.get('ime', '').strip()
            prezime = cleaned_data.get('prezime', '').strip()
            id_broj = cleaned_data.get('id_broj', '').strip()

            if not ime:
                self.add_error('ime', 'Ime je obavezno za fizička lica.')
            if not prezime:
                self.add_error('prezime', 'Prezime je obavezno za fizička lica.')
            # Story 5.1: ID broj is required for fizičko lice
            if not id_broj:
                self.add_error('id_broj', 'Broj lične karte / ID broj je obavezan za fizička lica.')

            # Update cleaned_data with stripped values
            cleaned_data['ime'] = ime
            cleaned_data['prezime'] = prezime
            cleaned_data['id_broj'] = id_broj

        elif entity_type == 'pravno':
            # ISSUE 12 FIX: Validate pravno lice fields with strip()
            naziv_organizacije = cleaned_data.get('naziv_organizacije', '').strip()
            registracioni_broj = cleaned_data.get('registracioni_broj', '').strip()

            if not naziv_organizacije:
                self.add_error('naziv_organizacije', 'Naziv organizacije je obavezan za pravna lica.')
            # Story 5.1: Registracioni broj is required for pravno lice
            if not registracioni_broj:
                self.add_error('registracioni_broj', 'Registracioni broj je obavezan za pravna lica.')

            # Update cleaned_data with stripped value
            cleaned_data['naziv_organizacije'] = naziv_organizacije
            cleaned_data['registracioni_broj'] = registracioni_broj

        return cleaned_data

    def clean_id_broj(self):
        """
        Validate and normalize ID broj format.

        Story 5.1: ID broj must be in format IDxxxxxx (ID + 6-7 digits)
        """
        id_broj = self.cleaned_data.get('id_broj')
        if id_broj:
            # Normalize: strip whitespace and convert to uppercase
            id_broj = id_broj.strip().upper()
            # Validate format using the validator
            validate_id_broj(id_broj)
        return id_broj

    def clean_registracioni_broj(self):
        """
        Validate and normalize Registracioni broj format.

        Story 5.1: Registracioni broj - alphanumeric, max 50 chars
        """
        registracioni_broj = self.cleaned_data.get('registracioni_broj')
        if registracioni_broj:
            # Normalize: strip whitespace
            registracioni_broj = registracioni_broj.strip()
            # Validate format using the validator
            validate_registracioni_broj(registracioni_broj)
        return registracioni_broj

    def clean_email(self):
        """
        Additional email validation: prevent disposable email domains.

        ISSUE 8 FIX: Proper docstring style (was inline comment).
        Currently uses Django's built-in EmailField validation only.
        Future enhancement: Block disposable domains (10minutemail, guerrillamail, etc.)
        """
        email = self.cleaned_data.get('email')
        if email:
            # Optional: Block disposable email domains (10minutemail, guerrillamail, etc.)
            # For now, just Django's built-in EmailField validation
            pass
        return email

    # Story 5.4+: Removed clean_telefon() normalization method
    # Phone validation now uses validate_phone from validators.py (6+ digits, no letters)


class COBInitiativeDataForm(forms.Form):
    """
    COB (Inicijativa) Section II - Initiative data validation.

    Story 3.5: Initial COB form
    Story 5.3: Added naziv_tima, date fields, totalni_budzet
              Renamed "Planirani koraci" to "Planirane aktivnosti"

    Architecture: Dual-layer validation (client-side + server-side)
    GDPR: Validation only, does NOT persist draft data
    """

    # Story 5.3: Naziv tima - FIRST field in Section II
    naziv_tima = forms.CharField(
        max_length=150,
        required=True,
        label='Naziv tima',
        error_messages={
            'required': 'Naziv tima je obavezan.',
            'max_length': 'Naziv tima ne može biti duži od 150 karaktera.',
        },
        widget=forms.TextInput(attrs={'maxlength': '150'})
    )

    # Naslov inicijative
    naslov = forms.CharField(
        max_length=150,
        required=True,
        label='Naslov inicijative',
        error_messages={
            'required': 'Naslov inicijative je obavezan.',
            'max_length': 'Naslov ne može biti duži od 150 karaktera.',
        },
        widget=forms.TextInput(attrs={'maxlength': '150'})
    )

    # Kratak opis
    kratak_opis = forms.CharField(
        max_length=500,
        required=True,
        label='Kratak opis',
        error_messages={
            'required': 'Kratak opis je obavezan.',
            'max_length': 'Kratak opis ne može biti duži od 500 karaktera.',
        },
        widget=forms.Textarea(attrs={'rows': 3, 'maxlength': '500'})
    )

    # Problem koji inicijativa rešava
    problem = forms.CharField(
        max_length=1500,
        required=True,
        label='Problem koji inicijativa rešava',
        error_messages={
            'required': 'Opis problema je obavezan.',
            'max_length': 'Opis problema ne može biti duži od 1500 karaktera.',
        },
        widget=forms.Textarea(attrs={'rows': 5, 'maxlength': '1500'})
    )

    # Cilj inicijative
    cilj = forms.CharField(
        max_length=1500,
        required=True,
        label='Cilj inicijative',
        error_messages={
            'required': 'Cilj inicijative je obavezan.',
            'max_length': 'Cilj inicijative ne može biti duži od 1500 karaktera.',
        },
        widget=forms.Textarea(attrs={'rows': 5, 'maxlength': '1500'})
    )

    # Story 5.3: Renamed from "Planirani koraci" to "Planirane aktivnosti"
    planirani_koraci = forms.CharField(
        max_length=1500,
        required=True,
        label='Planirane aktivnosti',  # Story 5.3: Changed label
        error_messages={
            'required': 'Planirane aktivnosti su obavezne.',
            'max_length': 'Planirane aktivnosti ne mogu biti duže od 1500 karaktera.',
        },
        widget=forms.Textarea(attrs={'rows': 5, 'maxlength': '1500'})
    )

    # Očekivani uticaj na zajednicu
    ocekivani_uticaj = forms.CharField(
        max_length=1500,
        required=True,
        label='Očekivani uticaj na zajednicu',
        error_messages={
            'required': 'Očekivani uticaj je obavezan.',
            'max_length': 'Očekivani uticaj ne može biti duži od 1500 karaktera.',
        },
        widget=forms.Textarea(attrs={'rows': 5, 'maxlength': '1500'})
    )

    # Story 5.3: Project timeline dates
    datum_startovanja = forms.DateField(
        required=True,
        label='Datum startovanja',
        error_messages={
            'required': 'Datum startovanja je obavezan.',
            'invalid': 'Neispravan format datuma.',
        },
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control date-picker',
        })
    )

    datum_zavrsetka = forms.DateField(
        required=True,
        label='Datum završetka',
        error_messages={
            'required': 'Datum završetka je obavezan.',
            'invalid': 'Neispravan format datuma.',
        },
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control date-picker',
        })
    )

    # Story 5.3: Total budget in EUR
    totalni_budzet = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=True,
        label='Totalni budžet (EUR)',
        error_messages={
            'required': 'Totalni budžet je obavezan.',
            'invalid': 'Neispravan format iznosa.',
            'max_digits': 'Iznos ima previše cifara.',
        },
        widget=forms.NumberInput(attrs={
            'step': '0.01',
            'min': '0',
            'placeholder': '0.00',
            'class': 'form-control budget-input',
        })
    )

    def clean_naziv_tima(self):
        """Normalize and validate naziv_tima."""
        naziv_tima = self.cleaned_data.get('naziv_tima')
        if naziv_tima:
            naziv_tima = naziv_tima.strip()
            if not naziv_tima:
                raise ValidationError('Naziv tima ne može biti prazan.')
        return naziv_tima

    def clean_naslov(self):
        """Normalize and validate naslov."""
        naslov = self.cleaned_data.get('naslov')
        if naslov:
            naslov = naslov.strip()
            if not naslov:
                raise ValidationError('Naslov ne može biti prazan.')
        return naslov

    def clean_kratak_opis(self):
        """Normalize and validate kratak_opis."""
        kratak_opis = self.cleaned_data.get('kratak_opis')
        if kratak_opis:
            kratak_opis = kratak_opis.strip()
            if not kratak_opis:
                raise ValidationError('Kratak opis ne može biti prazan.')
        return kratak_opis

    def clean_problem(self):
        """Normalize and validate problem."""
        problem = self.cleaned_data.get('problem')
        if problem:
            problem = problem.strip()
            if not problem:
                raise ValidationError('Opis problema ne može biti prazan.')
        return problem

    def clean_cilj(self):
        """Normalize and validate cilj."""
        cilj = self.cleaned_data.get('cilj')
        if cilj:
            cilj = cilj.strip()
            if not cilj:
                raise ValidationError('Cilj inicijative ne može biti prazan.')
        return cilj

    def clean_planirani_koraci(self):
        """Normalize and validate planirani_koraci (now called 'Planirane aktivnosti')."""
        planirani_koraci = self.cleaned_data.get('planirani_koraci')
        if planirani_koraci:
            planirani_koraci = planirani_koraci.strip()
            if not planirani_koraci:
                raise ValidationError('Planirane aktivnosti ne mogu biti prazne.')
        return planirani_koraci

    def clean_ocekivani_uticaj(self):
        """Normalize and validate ocekivani_uticaj."""
        ocekivani_uticaj = self.cleaned_data.get('ocekivani_uticaj')
        if ocekivani_uticaj:
            ocekivani_uticaj = ocekivani_uticaj.strip()
            if not ocekivani_uticaj:
                raise ValidationError('Očekivani uticaj ne može biti prazan.')
        return ocekivani_uticaj

    def clean_totalni_budzet(self):
        """Validate totalni_budzet - must be non-negative."""
        totalni_budzet = self.cleaned_data.get('totalni_budzet')
        if totalni_budzet is not None and totalni_budzet < 0:
            raise ValidationError('Budžet mora biti pozitivan broj.')
        return totalni_budzet

    def clean(self):
        """
        Cross-field validation for Section II.

        Story 5.3: Validates that datum_zavrsetka >= datum_startovanja
        """
        cleaned_data = super().clean()

        datum_startovanja = cleaned_data.get('datum_startovanja')
        datum_zavrsetka = cleaned_data.get('datum_zavrsetka')

        # Validate date range if both dates are provided
        if datum_startovanja and datum_zavrsetka:
            if datum_zavrsetka < datum_startovanja:
                self.add_error(
                    'datum_zavrsetka',
                    'Datum završetka ne može biti pre datuma startovanja.'
                )

        return cleaned_data


class COBSectionIIIForm(forms.Form):
    """
    COB (Inicijativa) Section III - Simplified documentation validation.
    Story 3.4: COB Section III - Simplified Documentation
    Story 5.4: Updated - BUDZET_INICIJATIVE required, PISMO_PODRSKE optional

    Differences from COA:
    - BUDZET_INICIJATIVE: Required, XLS/XLSX only
    - PISMO_PODRSKE: Optional, PDF/DOC/DOCX
    - Single checkbox: saglasnost_gdpr (required)

    Architecture: Backend validation only (files validated via metadata)
    GDPR: Validation only, does NOT persist files
    """

    # GDPR Consent Checkbox
    saglasnost_gdpr = forms.BooleanField(
        required=True,
        label='Prihvatam Politiku privatnosti i Uslove korišćenja',
        error_messages={
            'required': 'Saglasnost sa GDPR politikom je obavezna.',
        }
    )

    def clean(self):
        """
        Custom validation: Ensure saglasnost_gdpr is checked.

        ISSUE 11 FIX: Comprehensive docstring added.

        Validates GDPR consent checkbox is explicitly checked (True).
        This is a legal requirement for GDPR compliance - users MUST actively
        consent to data processing before submission.

        Architecture:
        - Called automatically by Django form validation pipeline
        - Runs AFTER individual field validation (clean_<field>() methods)
        - Adds field-specific error if checkbox is False/unchecked

        Returns:
            dict: Cleaned data dictionary with all validated fields

        Raises:
            ValidationError: Implicitly via add_error() if GDPR consent not checked
        """
        cleaned_data = super().clean()

        saglasnost = cleaned_data.get('saglasnost_gdpr')
        if not saglasnost:
            self.add_error('saglasnost_gdpr', 'Morate potvrditi saglasnost sa Politikom privatnosti i Uslovima korišćenja.')

        return cleaned_data


def validate_cob_file_metadata(file_metadata: Dict[str, Any]) -> Tuple[bool, Dict[str, List[Dict[str, str]]]]:
    """
    Validate COB file upload metadata structure.
    Story 3.4: COB Section III - File metadata validation
    Story 5.4: Updated - BUDZET_INICIJATIVE required (XLS/XLSX), PISMO_PODRSKE optional (PDF/DOC/DOCX)

    ISSUE 16 FIX: Added type hints
    ISSUE 1 FIX: Added file extension validation
    ISSUE 2 FIX: Added file size validation (max 10MB = 10485760 bytes)
    ISSUE 3 FIX: Return error objects with {'message': '...', 'code': '...'} format
    ISSUE 9 FIX: Removed redundant empty list check

    Expected structure:
    {
        'BUDZET_INICIJATIVE': [{'name': 'budget.xlsx', 'size': 1024000}],  # Required, XLS/XLSX
        'PISMO_PODRSKE': [{'name': 'pismo.pdf', 'size': 512000}]  # Optional, PDF/DOC/DOCX
    }

    Validation Rules:
    - BUDZET_INICIJATIVE is required, must be XLS or XLSX
    - PISMO_PODRSKE is optional, if present must be PDF/DOC/DOCX
    - Each category allows only 1 file
    - File size must not exceed 10MB (10485760 bytes)
    - File metadata must include 'name' and 'size' fields
    - File name cannot be empty string

    Args:
        file_metadata: File metadata from localStorage draft

    Returns:
        Tuple of (valid: bool, errors: dict with error objects)
        Error format: {'field': [{'message': '...', 'code': '...'}]}
    """
    errors: Dict[str, List[Dict[str, str]]] = {}

    if not isinstance(file_metadata, dict):
        return False, {'__all__': [{'message': 'Neispravan format metapodataka fajlova.', 'code': 'invalid_format'}]}

    # Story 5.4: Validate required categories (only BUDZET_INICIJATIVE is required)
    for category in COB_FILE_CATEGORIES_REQUIRED:
        if category not in file_metadata:
            errors[category] = [{'message': 'Budžet inicijative je obavezan.', 'code': 'missing_category'}]
        elif not file_metadata[category]:
            errors[category] = [{'message': 'Budžet inicijative je obavezan.', 'code': 'empty_list'}]
        elif not isinstance(file_metadata[category], list):
            errors[category] = [{'message': 'Neispravan format za budžet inicijative.', 'code': 'invalid_type'}]
        elif len(file_metadata[category]) > 1:
            errors[category] = [{'message': 'Budžet inicijative dozvoljava samo 1 fajl.', 'code': 'too_many_files'}]
        else:
            # Validate the budget file (must be XLS/XLSX)
            file_obj = file_metadata[category][0]
            error = _validate_file_object(file_obj, category, ALLOWED_EXCEL_EXTENSIONS)
            if error:
                errors[category] = [error]

    # Story 5.4: Validate optional categories (PISMO_PODRSKE)
    for category in COB_FILE_CATEGORIES_OPTIONAL:
        if category in file_metadata and file_metadata[category]:
            # Only validate if file is provided
            if not isinstance(file_metadata[category], list):
                errors[category] = [{'message': 'Neispravan format za pismo podrške.', 'code': 'invalid_type'}]
            elif len(file_metadata[category]) > 1:
                errors[category] = [{'message': 'Pismo podrške dozvoljava samo 1 fajl.', 'code': 'too_many_files'}]
            else:
                # Validate the support letter file (must be PDF/DOC/DOCX)
                file_obj = file_metadata[category][0]
                error = _validate_file_object(file_obj, category, ALLOWED_FILE_EXTENSIONS)
                if error:
                    errors[category] = [error]

    # Ensure NO other categories (COB should NOT have BUDGET, BIOGRAPHY, etc.)
    invalid_categories = set(file_metadata.keys()) - set(COB_FILE_CATEGORIES)
    if invalid_categories:
        errors['__all__'] = [{'message': f'Neočekivane kategorije fajlova: {", ".join(invalid_categories)}', 'code': 'unexpected_categories'}]

    return len(errors) == 0, errors


def _validate_file_object(file_obj: Any, category: str, allowed_extensions: List[str]) -> Optional[Dict[str, str]]:
    """
    Validate individual file object metadata.
    Story 5.4: Helper function for file validation

    Args:
        file_obj: File metadata object
        category: File category name
        allowed_extensions: List of allowed file extensions

    Returns:
        Error dict or None if valid
    """
    category_label = category.replace("_", " ").lower()

    if not isinstance(file_obj, dict):
        return {'message': f'Neispravan format metapodataka fajla za {category_label}.', 'code': 'invalid_file_object'}

    if 'name' not in file_obj:
        return {'message': f'Nedostaje ime fajla za {category_label}.', 'code': 'missing_name'}

    if 'size' not in file_obj:
        return {'message': f'Nedostaje veličina fajla za {category_label}.', 'code': 'missing_size'}

    file_name = file_obj.get('name', '')
    file_size = file_obj.get('size', 0)

    if not file_name or not file_name.strip():
        return {'message': f'Ime fajla ne može biti prazno za {category_label}.', 'code': 'empty_filename'}

    # Validate file extension
    file_ext = '.' + file_name.split('.')[-1].lower() if '.' in file_name else ''
    if file_ext not in allowed_extensions:
        ext_list = ', '.join(ext.upper().replace('.', '') for ext in allowed_extensions)
        return {'message': f'Dozvoljeni formati: {ext_list}', 'code': 'invalid_extension'}

    # Validate file size (max 10MB)
    try:
        file_size_int = int(file_size)
        if file_size_int > MAX_FILE_SIZE:
            return {'message': f'Fajl prelazi maksimalnu veličinu od 10MB (trenutna veličina: {file_size_int / 1048576:.2f}MB).', 'code': 'file_too_large'}
        elif file_size_int <= 0:
            return {'message': 'Veličina fajla mora biti veća od 0.', 'code': 'invalid_size'}
    except (ValueError, TypeError):
        return {'message': f'Neispravan format veličine fajla za {category_label}.', 'code': 'invalid_size_format'}

    return None
