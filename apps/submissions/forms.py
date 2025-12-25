# -*- coding: utf-8 -*-
"""
Django Forms for COA/COB application submission.
Story 2.2: COAFormSectionI - Section I (General Data Entry)
"""
from django import forms
from django.core.exceptions import ValidationError
from apps.submissions.models import Applicant, Application


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
