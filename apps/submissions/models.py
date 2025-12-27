# -*- coding: utf-8 -*-
"""
Models for COA and COB application submissions.

This module defines the data models for storing application submissions
and applicant information in the DOMOVIK system.
"""

from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError


class Application(models.Model):
    """
    Application model for storing COA and COB submissions.

    Represents a single application submission, either for a Project (COA)
    or Initiative (COB). Each application has one associated applicant.

    Fields:
        reference_number: Unique identifier (format: COA-YYYY-NNN or COB-YYYY-NNN)
        type: Application type (COA or COB)
        status: Current application status
        created_at: Timestamp when application was created
        submitted_at: Timestamp when application was submitted (null until submitted)
        updated_at: Timestamp of last update
    """

    TYPE_CHOICES = [
        ('COA', 'Prijava za Projekat'),
        ('COB', 'Prijava za Inicijativu'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Podneto'),
        ('under_review', 'U Razmatranju'),
        ('approved', 'Odobreno'),
        ('rejected', 'Odbijeno'),
    ]

    reference_number = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        verbose_name='Referentni Broj',
        help_text='Format: COA-YYYY-NNN ili COB-YYYY-NNN'
    )

    type = models.CharField(
        max_length=3,
        choices=TYPE_CHOICES,
        verbose_name='Tip Prijave'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name='Status'
    )

    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name='Kreirano'
    )

    submitted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Podneseno'
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Ažurirano'
    )

    # Section II: Project Data (Story 2.6)
    naslov = models.CharField(
        max_length=150,
        blank=True,
        verbose_name='Naslov projekta',
        help_text='Maksimalno 150 karaktera'
    )

    opis = models.TextField(
        blank=True,
        verbose_name='Kratak opis',
        help_text='Maksimalno 500 karaktera'
    )

    problem = models.TextField(
        blank=True,
        verbose_name='Problem koji se rešava',
        help_text='Maksimalno 2000 karaktera'
    )

    cilj = models.TextField(
        blank=True,
        verbose_name='Glavni cilj',
        help_text='Maksimalno 1000 karaktera'
    )

    specifični_ciljevi = models.TextField(
        blank=True,
        verbose_name='Specifični ciljevi',
        help_text='Maksimalno 1000 karaktera'
    )

    ciljne_grupe = models.TextField(
        blank=True,
        verbose_name='Ciljne grupe',
        help_text='Maksimalno 1500 karaktera'
    )

    aktivnosti = models.TextField(
        blank=True,
        verbose_name='Aktivnosti',
        help_text='Maksimalno 1500 karaktera'
    )

    rezultati = models.TextField(
        blank=True,
        verbose_name='Rezultati',
        help_text='Maksimalno 1500 karaktera'
    )

    budžet = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Totalni budžet (RSD)',
        help_text='Iznos u dinarima'
    )

    class Meta:
        ordering = ['-submitted_at', '-created_at']
        verbose_name = 'Prijava'
        verbose_name_plural = 'Prijave'
        indexes = [
            models.Index(fields=['reference_number']),
            models.Index(fields=['type', 'status']),
            models.Index(fields=['submitted_at']),
        ]

    def __str__(self):
        """Return string representation of application."""
        return f"{self.reference_number} ({self.get_type_display()})"

    def clean(self):
        """
        Validate application data.

        Validates that type field is one of the allowed choices.

        Raises:
            ValidationError: If validation fails
        """
        super().clean()

        # Validate type field
        valid_types = [choice[0] for choice in self.TYPE_CHOICES]
        if self.type and self.type not in valid_types:
            raise ValidationError({
                'type': f"Invalid type '{self.type}'. Must be one of: {', '.join(valid_types)}"
            })

    def save(self, *args, **kwargs):
        """
        Save application instance.

        Auto-generates reference_number if not set.
        Auto-sets submitted_at timestamp when status becomes 'submitted'.
        Note: Full reference number generation implemented in Story 2.11.
        """
        if not self.reference_number:
            self.reference_number = self._generate_reference_number()

        # Auto-set submitted_at when status changes to 'submitted'
        if self.status == 'submitted' and not self.submitted_at:
            self.submitted_at = timezone.now()

        super().save(*args, **kwargs)

    def _generate_reference_number(self):
        """
        Generate unique reference number for application.

        TODO: Full implementation in Story 2.11 (Submission Processing).
        For Story 2.1, this is a placeholder stub with unique UUID suffix.

        Returns:
            str: Placeholder reference number (format: TYPE-YYYY-TEMP-xxxxxx)
        """
        import uuid
        # Placeholder stub - full implementation in Story 2.11
        # Use dynamic year and UUID suffix to ensure uniqueness
        year = timezone.now().year
        unique_suffix = uuid.uuid4().hex[:6]
        return f"{self.type}-{year}-TEMP-{unique_suffix}"


class Applicant(models.Model):
    """
    Applicant model for storing submitter information.

    Stores information about the person or organization submitting an application.
    Supports both individual (fizičko lice) and legal entity (pravno lice) applicants.

    Fields:
        application: One-to-one link to Application
        entity_type: Type of applicant (fizičko or pravno)
        ime: First name (fizičko lice only)
        prezime: Last name (fizičko lice only)
        jmbg: Personal ID number (fizičko lice, COA only)
        naziv_organizacije: Organization name (pravno lice only)
        maticni_broj: Registration number (pravno lice, COA only)
        adresa: Address (required for both types)
        email: Email address (required for both types)
        telefon: Phone number (required for both types)
    """

    ENTITY_TYPE_CHOICES = [
        ('fizicko', 'Fizičko Lice'),
        ('pravno', 'Pravno Lice'),
    ]

    application = models.OneToOneField(
        Application,
        on_delete=models.CASCADE,
        related_name='applicant',
        verbose_name='Prijava'
    )

    entity_type = models.CharField(
        max_length=10,
        choices=ENTITY_TYPE_CHOICES,
        verbose_name='Tip Podnosioca'
    )

    # Fizičko lice fields
    ime = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Ime'
    )

    prezime = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Prezime'
    )

    jmbg = models.CharField(
        max_length=13,
        blank=True,
        verbose_name='JMBG',
        help_text='13 cifara'
    )

    # Pravno lice fields
    naziv_organizacije = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Naziv Organizacije'
    )

    maticni_broj = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Matični Broj'
    )

    # Common fields
    adresa = models.CharField(
        max_length=300,
        verbose_name='Adresa'
    )

    email = models.EmailField(
        verbose_name='Email'
    )

    telefon = models.CharField(
        max_length=20,
        verbose_name='Telefon'
    )

    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name='Kreirano'
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Ažurirano'
    )

    class Meta:
        verbose_name = 'Podnosilac'
        verbose_name_plural = 'Podnosioci'

    def __str__(self):
        """Return string representation of applicant."""
        if self.entity_type == 'fizicko':
            return f"{self.ime} {self.prezime}"
        else:
            return self.naziv_organizacije

    def clean(self):
        """
        Validate applicant data based on entity type and application type.

        Validation rules:
        - Fizičko lice: ime and prezime required
        - Pravno lice: naziv_organizacije required
        - COA fizičko: JMBG required (13 digits)
        - COA pravno: matični broj required
        - COB: JMBG and matični NOT required

        Raises:
            ValidationError: If validation fails
        """
        super().clean()

        # Validate based on entity type
        if self.entity_type == 'fizicko':
            if not self.ime or not self.prezime:
                raise ValidationError({
                    'ime': 'Ime je obavezno za fizička lica.',
                    'prezime': 'Prezime je obavezno za fizička lica.'
                })
        elif self.entity_type == 'pravno':
            if not self.naziv_organizacije:
                raise ValidationError({
                    'naziv_organizacije': 'Naziv organizacije je obavezan za pravna lica.'
                })

        # CRITICAL: Application must be saved before this validation
        # Django form processing: Create Application → Save → Create Applicant → Link → Validate
        if self.application_id and self.application.type == 'COA':
            # COA requires JMBG for fizičko lice
            if self.entity_type == 'fizicko':
                if not self.jmbg:
                    raise ValidationError({
                        'jmbg': 'JMBG je obavezan za fizička lica u COA prijavama.'
                    })
                if len(self.jmbg) != 13 or not self.jmbg.isdigit():
                    raise ValidationError({
                        'jmbg': 'JMBG mora imati tačno 13 cifara.'
                    })

            # COA requires matični broj for pravno lice
            elif self.entity_type == 'pravno':
                if not self.maticni_broj:
                    raise ValidationError({
                        'maticni_broj': 'Matični broj je obavezan za pravna lica u COA prijavama.'
                    })


class UploadedFile(models.Model):
    """
    Model for storing uploaded file metadata.

    Stores metadata about files uploaded by users (budgets, biographies, support letters).
    Files are linked to sessions during draft phase and to applications after submission.

    Security Features:
    - Unique filenames (timestamp + UUID + sanitized original)
    - Storage outside web root (media/uploads/)
    - Session-based ownership validation
    - MIME type validation to prevent spoofing
    - Extension whitelist enforcement
    - Size limit enforcement (10MB max)

    Fields:
        original_filename: Original name of uploaded file
        stored_filename: Unique filename used for storage
        file_path: Path to file in media storage
        file_size: Size in bytes
        file_type: File extension (pdf, doc, docx, xls, xlsx)
        mime_type: Detected MIME type
        category: File category (budget, biography, support letter)
        upload_date: When file was uploaded
        uploaded_by_session: Session key of uploader
        application: Linked application (null for drafts)
        is_deleted: Soft delete flag
    """

    CATEGORY_CHOICES = [
        ('BUDGET', 'Budžet'),
        ('BIOGRAPHY', 'Biografija'),
        ('SUPPORT_LETTER', 'Pismo Podrške'),
    ]

    original_filename = models.CharField(
        max_length=255,
        verbose_name='Originalni Naziv',
        help_text='Original file name as uploaded by user'
    )

    stored_filename = models.CharField(
        max_length=255,
        unique=True,
        verbose_name='Naziv u Skladištu',
        help_text='Unique filename used for storage'
    )

    file_path = models.FileField(
        upload_to='uploads/%Y/%m/%d/',
        verbose_name='Putanja Fajla'
    )

    file_size = models.IntegerField(
        verbose_name='Veličina Fajla',
        help_text='Size in bytes'
    )

    file_type = models.CharField(
        max_length=10,
        verbose_name='Tip Fajla',
        help_text='File extension: pdf, doc, docx, xls, xlsx'
    )

    mime_type = models.CharField(
        max_length=100,
        verbose_name='MIME Tip',
        help_text='Detected MIME type for validation'
    )

    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        verbose_name='Kategorija',
        help_text='Purpose of uploaded file'
    )

    upload_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Datum Upload-a'
    )

    uploaded_by_session = models.CharField(
        max_length=40,
        db_index=True,
        verbose_name='Sesija Korisnika',
        help_text='Session key for draft file ownership'
    )

    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='uploaded_files',
        verbose_name='Prijava',
        help_text='Linked application (null for draft files)'
    )

    is_deleted = models.BooleanField(
        default=False,
        verbose_name='Obrisan',
        help_text='Soft delete flag'
    )

    class Meta:
        ordering = ['-upload_date']
        verbose_name = 'Upload-ovani Fajl'
        verbose_name_plural = 'Upload-ovani Fajlovi'
        indexes = [
            models.Index(fields=['uploaded_by_session']),
            models.Index(fields=['application']),
            models.Index(fields=['upload_date']),
            models.Index(fields=['is_deleted']),
        ]

    def __str__(self):
        """Return string representation of uploaded file."""
        return f"{self.original_filename} ({self.file_type})"
