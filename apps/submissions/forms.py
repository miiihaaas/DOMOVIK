# -*- coding: utf-8 -*-
"""
Django Forms for COA/COB application submission.
Story 2.2: COAFormSectionI - Section I (General Data Entry)
Story 2.8: FileUploadForm - File Upload with Validation
"""
from django import forms
from django.core.exceptions import ValidationError
from apps.submissions.models import Applicant, Application
from apps.submissions.validators import (
    validate_file_extension,
    validate_file_size,
    validate_mime_type
)


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
            'ime', 'prezime', 'jmbg',
            # Pravno lice fields
            'naziv_organizacije', 'maticni_broj',
            # Common fields
            'adresa', 'email', 'telefon'
        ]

        widgets = {
            'entity_type': forms.HiddenInput(),  # Handled by JavaScript switcher
            'adresa': forms.Textarea(attrs={'rows': 3}),
        }

        labels = {
            'entity_type': 'Tip podnosioca',
            'ime': 'Ime',
            'prezime': 'Prezime',
            'jmbg': 'JMBG',
            'naziv_organizacije': 'Naziv organizacije',
            'maticni_broj': 'Matični broj',
            'adresa': 'Adresa',
            'email': 'Email adresa',
            'telefon': 'Broj telefona',
        }

        help_texts = {
            'jmbg': '13 cifara (npr. 1234567890123)',
            'email': 'npr. marko@example.com',
            'telefon': 'npr. 0611234567',
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
        try:
            # Mock Application instance (required for Applicant validation)
            # Save it temporarily to get ID (required for Applicant.clean() COA checks)
            mock_app = Application(type='COA')
            mock_app.save()  # Need ID for application_id check in Applicant.clean()

            try:
                # Create Applicant with form data
                # Use all cleaned_data fields (including empty strings) for proper validation
                applicant = Applicant(application=mock_app, **cleaned_data)

                # Run model validation - this delegates to Applicant.clean()
                applicant.clean()
            finally:
                # Clean up: Delete temporary Application instance
                mock_app.delete()

        except ValidationError as e:
            # Convert model ValidationError to form errors
            if hasattr(e, 'message_dict'):
                # Field-specific errors
                for field, errors in e.message_dict.items():
                    for error in errors:
                        self.add_error(field, error)
            else:
                # Non-field errors
                for error in e.messages:
                    self.add_error(None, error)

        return cleaned_data


class COAFormSectionII(forms.ModelForm):
    """
    COA Form Section II - Project Data Entry with Character Management
    Story 2.6: Section II fields with character limits and budget validation

    Handles project data including naslov, opis, problem, cilj, etc.
    Client-side character counting managed by character-counter.js.
    Server-side validation ensures data integrity.
    """

    class Meta:
        model = Application
        fields = [
            'naslov', 'opis', 'problem', 'cilj',
            'specifični_ciljevi', 'ciljne_grupe',
            'aktivnosti', 'rezultati', 'budžet'
        ]

        widgets = {
            'naslov': forms.Textarea(attrs={'rows': 3}),
            'opis': forms.Textarea(attrs={'rows': 5}),
            'problem': forms.Textarea(attrs={'rows': 10}),
            'cilj': forms.Textarea(attrs={'rows': 8}),
            'specifični_ciljevi': forms.Textarea(attrs={'rows': 8}),
            'ciljne_grupe': forms.Textarea(attrs={'rows': 10}),
            'aktivnosti': forms.Textarea(attrs={'rows': 10}),
            'rezultati': forms.Textarea(attrs={'rows': 10}),
            'budžet': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'placeholder': '0.00'}),
        }

        labels = {
            'naslov': 'Naslov projekta',
            'opis': 'Kratak opis',
            'problem': 'Problem koji se rešava',
            'cilj': 'Glavni cilj',
            'specifični_ciljevi': 'Specifični ciljevi',
            'ciljne_grupe': 'Ciljne grupe',
            'aktivnosti': 'Aktivnosti',
            'rezultati': 'Rezultati',
            'budžet': 'Totalni budžet (RSD)',
        }

        help_texts = {
            'naslov': 'Maksimalno 150 karaktera',
            'opis': 'Maksimalno 500 karaktera',
            'problem': 'Maksimalno 2000 karaktera',
            'cilj': 'Maksimalno 1000 karaktera',
            'specifični_ciljevi': 'Maksimalno 1000 karaktera',
            'ciljne_grupe': 'Maksimalno 1500 karaktera',
            'aktivnosti': 'Maksimalno 1500 karaktera',
            'rezultati': 'Maksimalno 1500 karaktera',
            'budžet': 'Unesite iznos u dinarima (npr. 1000000)',
        }

    def clean_naslov(self):
        """Validate naslov field - max 150 characters."""
        naslov = self.cleaned_data.get('naslov', '')
        if len(naslov) > 150:
            raise ValidationError('Naslov ne može biti duži od 150 karaktera.')
        return naslov

    def clean_opis(self):
        """Validate opis field - max 500 characters."""
        opis = self.cleaned_data.get('opis', '')
        if len(opis) > 500:
            raise ValidationError('Opis ne može biti duži od 500 karaktera.')
        return opis

    def clean_problem(self):
        """Validate problem field - max 2000 characters."""
        problem = self.cleaned_data.get('problem', '')
        if len(problem) > 2000:
            raise ValidationError('Problem ne može biti duži od 2000 karaktera.')
        return problem

    def clean_cilj(self):
        """Validate cilj field - max 1000 characters."""
        cilj = self.cleaned_data.get('cilj', '')
        if len(cilj) > 1000:
            raise ValidationError('Glavni cilj ne može biti duži od 1000 karaktera.')
        return cilj

    def clean_specifični_ciljevi(self):
        """Validate specifični_ciljevi field - max 1000 characters."""
        specifični_ciljevi = self.cleaned_data.get('specifični_ciljevi', '')
        if len(specifični_ciljevi) > 1000:
            raise ValidationError('Specifični ciljevi ne mogu biti duži od 1000 karaktera.')
        return specifični_ciljevi

    def clean_ciljne_grupe(self):
        """Validate ciljne_grupe field - max 1500 characters."""
        ciljne_grupe = self.cleaned_data.get('ciljne_grupe', '')
        if len(ciljne_grupe) > 1500:
            raise ValidationError('Ciljne grupe ne mogu biti duže od 1500 karaktera.')
        return ciljne_grupe

    def clean_aktivnosti(self):
        """Validate aktivnosti field - max 1500 characters."""
        aktivnosti = self.cleaned_data.get('aktivnosti', '')
        if len(aktivnosti) > 1500:
            raise ValidationError('Aktivnosti ne mogu biti duže od 1500 karaktera.')
        return aktivnosti

    def clean_rezultati(self):
        """Validate rezultati field - max 1500 characters."""
        rezultati = self.cleaned_data.get('rezultati', '')
        if len(rezultati) > 1500:
            raise ValidationError('Rezultati ne mogu biti duži od 1500 karaktera.')
        return rezultati

    def clean_budžet(self):
        """Validate budžet field - positive number only."""
        budžet = self.cleaned_data.get('budžet')
        if budžet is not None and budžet < 0:
            raise ValidationError('Budžet mora biti pozitivan broj.')
        return budžet


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
