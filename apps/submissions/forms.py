# -*- coding: utf-8 -*-
"""
Django Forms for COA/COB application submission.
Story 2.2: COAFormSectionI - Section I (General Data Entry)
Story 2.8: FileUploadForm - File Upload with Validation
Story 2.11: Updated for ProjectData model separation
"""
from django import forms
from django.core.exceptions import ValidationError
from apps.submissions.models import Applicant, Application, ProjectData
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
