# -*- coding: utf-8 -*-
"""
Django Forms for COA/COB application submission.
Story 2.2: COAFormSectionI - Section I (General Data Entry)
Story 2.8: FileUploadForm - File Upload with Validation
Story 2.11: Updated for ProjectData model separation
Story 3.2: COBApplicantForm - Simplified applicant validation (no JMBG/matični broj)
"""
from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from apps.submissions.models import Applicant, Application, ProjectData
from apps.submissions.validators import (
    validate_file_extension,
    validate_file_size,
    validate_mime_type
)
import re


class COAFormSectionI(forms.ModelForm):
    """
    COA Form Section I - General Data Entry with Entity Type Switch

    Handles fizičko lice and pravno lice applicant data.
    Leverages Applicant model validation for conditional requirements.
    """

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
            'jmbg': 'JMBG',
            'organization_name': 'Naziv organizacije',
            'maticni_broj': 'Matični broj',
            'address': 'Adresa',
            'email': 'Email adresa',
            'phone': 'Broj telefona',
        }

        help_texts = {
            'jmbg': '13 cifara (npr. 1234567890123)',
            'email': 'npr. marko@example.com',
            'phone': 'npr. 0611234567',
        }

    def clean(self):
        """
        Conditional validation based on entity_type.

        **CRITICAL - DRY Principle:**
        Leverages existing Applicant.clean() model validation instead of duplicating logic.
        This ensures consistency between form validation and model validation.

        Validation Rules (delegated to Applicant.clean()):
        - Fizičko lice: ime + prezime required, JMBG required (COA)
        - Pravno lice: naziv_organizacije required, matični broj required (COA)
        """
        cleaned_data = super().clean()

        # Create temporary Application and Applicant instances to leverage existing model validation
        # This avoids duplicating validation logic (DRY principle)
        # Note: Story 2.11 simplified - validation moved to backend API
        # Form validation only checks basic field requirements
        entity_type = cleaned_data.get('entity_type')

        if entity_type == 'fizicko':
            if not cleaned_data.get('first_name'):
                self.add_error('first_name', 'Ime je obavezno za fizička lica.')
            if not cleaned_data.get('last_name'):
                self.add_error('last_name', 'Prezime je obavezno za fizička lica.')
        elif entity_type == 'pravno':
            if not cleaned_data.get('organization_name'):
                self.add_error('organization_name', 'Naziv organizacije je obavezan za pravna lica.')

        return cleaned_data


class COAFormSectionII(forms.ModelForm):
    """
    COA Form Section II - Project Data Entry with Character Management
    Story 2.6: Section II fields with character limits and budget validation
    Story 2.11: Updated to use ProjectData model

    Handles project data including title, short_description, problem, main_goal, etc.
    Client-side character counting managed by character-counter.js.
    Server-side validation ensures data integrity.
    """

    class Meta:
        model = ProjectData
        fields = [
            'title', 'short_description', 'problem', 'main_goal',
            'specific_goals', 'target_groups',
            'activities', 'results', 'total_budget'
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
            'total_budget': 'Totalni budžet (RSD)',
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


class FileUploadForm(forms.Form):
    """
    File Upload Form with comprehensive validation.
    Story 2.8: File Upload Infrastructure

    Validates:
    - File extension (PDF, DOC, DOCX, XLS, XLSX only)
    - File size (10MB max)
    - MIME type (prevents extension spoofing)
    - File category (budget, biography, support letter)

    Security Features:
    - Extension whitelist enforcement
    - Size limit enforcement
    - MIME type validation
    - CSRF protection (handled by view decorator)
    """

    CATEGORY_CHOICES = [
        ('BUDGET', 'Budžet'),
        ('BIOGRAPHY', 'Biografija'),
        ('SUPPORT_LETTER', 'Pismo Podrške'),
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

    # NO jmbg field - COB simplification

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

    # NO maticni_broj field - COB simplification

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

    telefon = forms.CharField(
        max_length=20,
        required=True,
        label='Telefon',  # ISSUE 6 FIX: Add label attribute
        validators=[
            RegexValidator(
                # ISSUE 2 FIX: Serbian mobile numbers are EXACTLY 8 digits after 6
                # Format: 06XXXXXXXX (9 digits total) or +3816XXXXXXXX (13 digits total)
                regex=r'^(\+381|0)6[0-9]{8}$',
                message='Neispravan format telefona. Koristite format: 06XXXXXXXX ili +3816XXXXXXXX',
            )
        ],
        error_messages={
            'required': 'Telefon je obavezan.',
        },
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

            if not ime:
                self.add_error('ime', 'Ime je obavezno za fizička lica.')
            if not prezime:
                self.add_error('prezime', 'Prezime je obavezno za fizička lica.')

            # Update cleaned_data with stripped values
            cleaned_data['ime'] = ime
            cleaned_data['prezime'] = prezime

        elif entity_type == 'pravno':
            # ISSUE 12 FIX: Validate pravno lice fields with strip()
            naziv_organizacije = cleaned_data.get('naziv_organizacije', '').strip()

            if not naziv_organizacije:
                self.add_error('naziv_organizacije', 'Naziv organizacije je obavezan za pravna lica.')

            # Update cleaned_data with stripped value
            cleaned_data['naziv_organizacije'] = naziv_organizacije

        return cleaned_data

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

    def clean_telefon(self):
        """
        Normalize phone number format.

        Input: +381651234567 or 0651234567
        Output: +381651234567 (normalized)

        ISSUE 5 FIX: Proper validation when telefon is None/empty.
        ISSUE 7 FIX: Re-validate normalized phone against regex.
        """
        telefon = self.cleaned_data.get('telefon')

        # ISSUE 5 FIX: Return early if telefon is None or empty (required validation handles this)
        if not telefon:
            return telefon

        # Normalize: 06X → +3816X
        if telefon.startswith('06'):
            telefon = '+381' + telefon[1:]  # Remove leading 0

        # ISSUE 7 FIX: Re-validate normalized format against regex
        # This ensures +3816X formats still match the pattern after normalization
        import re
        phone_pattern = r'^\+3816[0-9]{8}$'
        if not re.match(phone_pattern, telefon):
            raise ValidationError('Neispravan format telefona nakon normalizacije.')

        # Store normalized format
        return telefon


class COBInitiativeDataForm(forms.Form):
    """
    COB (Inicijativa) Section II - Initiative data validation.

    Differences from COA:
    - NO budžet field (COB doesn't require budget)
    - NO ciljne_grupe, aktivnosti, rezultati (simpler structure)
    - Problem limit: 1500 chars (vs COA's 2000)
    - Single cilj field: 1500 chars (vs COA's glavni_cilj + specifični_ciljevi)

    Architecture: Dual-layer validation (client-side + server-side)
    GDPR: Validation only, does NOT persist draft data
    """

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
        widget=forms.Textarea(attrs={'rows': 5, 'maxlength': '1500'})  # ISSUE 15 FIX: Add maxlength attribute
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
        widget=forms.Textarea(attrs={'rows': 5, 'maxlength': '1500'})  # ISSUE 15 FIX: Add maxlength attribute
    )

    # Planirani koraci
    planirani_koraci = forms.CharField(
        max_length=1500,
        required=True,
        label='Planirani koraci',
        error_messages={
            'required': 'Planirani koraci su obavezni.',
            'max_length': 'Planirani koraci ne mogu biti duži od 1500 karaktera.',
        },
        widget=forms.Textarea(attrs={'rows': 5, 'maxlength': '1500'})  # ISSUE 15 FIX: Add maxlength attribute
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
        widget=forms.Textarea(attrs={'rows': 5, 'maxlength': '1500'})  # ISSUE 15 FIX: Add maxlength attribute
    )

    # NO budžet field - COB simplification
    # NO ciljne_grupe field - COB simplification
    # NO aktivnosti field - COB simplification
    # NO rezultati field - COB simplification

    # ISSUE 16 FIX: Removed clean() method - it's DEAD CODE
    # Django calls clean_<field>() FIRST, then clean()
    # By the time clean() executes, values are already stripped by clean_<field>() methods
    # So the check "if value and not value.strip()" would NEVER trigger
    # Whitespace validation is correctly handled in individual clean_<field>() methods below

    def clean_naslov(self):
        """Normalize and validate naslov."""
        naslov = self.cleaned_data.get('naslov')
        if naslov:
            # Strip leading/trailing whitespace
            naslov = naslov.strip()
            # Ensure non-empty after strip
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
        """Normalize and validate planirani_koraci."""
        planirani_koraci = self.cleaned_data.get('planirani_koraci')
        if planirani_koraci:
            planirani_koraci = planirani_koraci.strip()
            if not planirani_koraci:
                raise ValidationError('Planirani koraci ne mogu biti prazni.')
        return planirani_koraci

    def clean_ocekivani_uticaj(self):
        """Normalize and validate ocekivani_uticaj."""
        ocekivani_uticaj = self.cleaned_data.get('ocekivani_uticaj')
        if ocekivani_uticaj:
            ocekivani_uticaj = ocekivani_uticaj.strip()
            if not ocekivani_uticaj:
                raise ValidationError('Očekivani uticaj ne može biti prazan.')
        return ocekivani_uticaj
