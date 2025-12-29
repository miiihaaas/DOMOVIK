# -*- coding: utf-8 -*-
"""
Models for COA and COB application submissions.

This module defines the data models for storing application submissions
and applicant information in the DOMOVIK system.

Story 2.11: Added ReferenceNumberSequence, ProjectData, FileMetadata models
Story 2.11: Using constants from constants.py
Story 2.15: Added DraftMetadata model for GDPR-compliant draft tracking
"""

import uuid
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from apps.submissions.constants import ApplicationType, ApplicationStatus, EntityType, FileType


class ReferenceNumberSequence(models.Model):
    """
    Track sequential reference numbers per year and application type.

    This model ensures unique, sequential reference numbers without gaps.
    Uses database row locking (select_for_update) to prevent race conditions.

    Fields:
        year: Year for this sequence (e.g., 2025)
        application_type: COA or COB
        last_number: Last assigned sequential number
    """
    year = models.IntegerField(
        verbose_name='Godina',
        help_text='Year for this sequence'
    )

    application_type = models.CharField(
        max_length=10,
        choices=ApplicationType.CHOICES,
        verbose_name='Tip prijave'
    )

    last_number = models.IntegerField(
        default=0,
        verbose_name='Poslednji Broj',
        help_text='Last assigned sequential number'
    )

    class Meta:
        unique_together = [['year', 'application_type']]
        verbose_name = 'Sekvenca Referentnog Broja'
        verbose_name_plural = 'Sekvence Referentnih Brojeva'
        indexes = [
            models.Index(fields=['year', 'application_type']),
        ]

    def __str__(self):
        """Return string representation of sequence."""
        return f"{self.application_type}-{self.year}: {self.last_number:03d}"


class Application(models.Model):
    """
    Application model for storing COA and COB submissions.

    Represents a single application submission, either for a Project (COA)
    or Initiative (COB). Each application has one associated applicant.
    Project details for COA are stored in separate ProjectData model.

    Fields:
        reference_number: Unique identifier (format: COA-YYYY-NNN or COB-YYYY-NNN)
        application_type: Application type (COA or COB)
        status: Current application status
        created_at: Timestamp when application was created
        submitted_at: Timestamp when application was submitted (null until submitted)
    """

    reference_number = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        verbose_name='Referentni Broj',
        help_text='Format: COA-YYYY-NNN ili COB-YYYY-NNN'
    )

    application_type = models.CharField(
        max_length=3,
        choices=ApplicationType.CHOICES,
        db_index=True,
        verbose_name='Tip prijave'
    )

    status = models.CharField(
        max_length=20,
        choices=ApplicationStatus.CHOICES,
        default=ApplicationStatus.SUBMITTED,
        db_index=True,
        verbose_name='Status'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Kreirano'
    )

    submitted_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name='Podneseno'
    )

    class Meta:
        ordering = ['-submitted_at', '-created_at']
        verbose_name = 'Prijava'
        verbose_name_plural = 'Prijave'
        indexes = [
            models.Index(fields=['reference_number']),
            models.Index(fields=['application_type', 'status']),
            models.Index(fields=['submitted_at']),
        ]

    def __str__(self):
        """Return string representation of application."""
        return f"{self.reference_number} ({self.get_application_type_display()})"


class Applicant(models.Model):
    """
    Applicant model for storing submitter information.

    Stores information about the person or organization submitting an application.
    Supports both individual (fizičko lice) and legal entity (pravno lice) applicants.

    Fields:
        application: One-to-one link to Application
        entity_type: Type of applicant (fizicko or pravno)
        first_name: First name (fizičko lice only)
        last_name: Last name (fizičko lice only)
        jmbg: Personal ID number (fizičko lice, COA only)
        organization_name: Organization name (pravno lice only)
        maticni_broj: Registration number (pravno lice, COA only)
        address: Address (required for both types)
        email: Email address (required for both types)
        phone: Phone number (required for both types)
    """

    application = models.OneToOneField(
        Application,
        on_delete=models.CASCADE,
        related_name='applicant',
        verbose_name='Prijava'
    )

    entity_type = models.CharField(
        max_length=10,
        choices=EntityType.CHOICES,
        verbose_name='Tip Podnosioca',
        db_index=True  # ISSUE 2 FIX: Index for EntityTypeFilter performance
    )

    # Fizičko lice fields
    first_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Ime'
    )

    last_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Prezime'
    )

    jmbg = models.CharField(
        max_length=13,
        blank=True,
        null=True,
        verbose_name='JMBG',
        help_text='13 cifara'
    )

    # Pravno lice fields
    organization_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Naziv Organizacije'
    )

    maticni_broj = models.CharField(
        max_length=8,
        blank=True,
        null=True,
        verbose_name='Matični Broj',
        help_text='8 cifara'
    )

    # Common fields
    address = models.CharField(
        max_length=300,
        verbose_name='Adresa'
    )

    email = models.EmailField(
        db_index=True,
        verbose_name='Email'
    )

    phone = models.CharField(
        max_length=20,
        verbose_name='Telefon'
    )

    class Meta:
        verbose_name = 'Podnosilac'
        verbose_name_plural = 'Podnosioci'
        # Index on email for duplicate detection queries (Story 2.11)
        indexes = [
            models.Index(fields=['email'], name='applicant_email_idx'),
        ]

    def __str__(self):
        """Return string representation of applicant."""
        if self.entity_type == EntityType.FIZICKO:
            return f"{self.first_name} {self.last_name}"
        else:
            return self.organization_name


class ProjectData(models.Model):
    """
    Project data for COA submissions only.

    Stores detailed project information for COA applications.
    This model has a OneToOne relationship with Application.

    Fields:
        application: Link to Application (OneToOne)
        title: Project title (max 150 chars)
        short_description: Brief description (max 500 chars)
        problem: Problem being addressed (max 2000 chars)
        main_goal: Main objective (max 1000 chars)
        specific_goals: Specific objectives (max 1000 chars)
        target_groups: Target beneficiaries (max 1500 chars)
        activities: Planned activities (max 1500 chars)
        results: Expected outcomes (max 1500 chars)
        total_budget: Total budget amount in RSD
    """

    application = models.OneToOneField(
        Application,
        on_delete=models.CASCADE,
        related_name='project_data',
        verbose_name='Prijava'
    )

    title = models.CharField(
        max_length=150,
        verbose_name='Naslov Projekta'
    )

    short_description = models.TextField(
        max_length=500,
        verbose_name='Kratak Opis'
    )

    problem = models.TextField(
        max_length=2000,
        verbose_name='Problem'
    )

    main_goal = models.TextField(
        max_length=1000,
        verbose_name='Glavni Cilj'
    )

    specific_goals = models.TextField(
        max_length=1000,
        verbose_name='Specifični Ciljevi'
    )

    target_groups = models.TextField(
        max_length=1500,
        verbose_name='Ciljne Grupe'
    )

    activities = models.TextField(
        max_length=1500,
        verbose_name='Aktivnosti'
    )

    results = models.TextField(
        max_length=1500,
        verbose_name='Rezultati'
    )

    total_budget = models.IntegerField(
        verbose_name='Ukupan Budžet',
        help_text='Iznos u RSD'
    )

    class Meta:
        verbose_name = 'Podaci Projekta'
        verbose_name_plural = 'Podaci Projekata'

    def __str__(self):
        """Return string representation of project data."""
        return f"ProjectData: {self.title[:50]}"


class InitiativeData(models.Model):
    """
    COB (Inicijativa) - Initiative-specific data.

    Differences from ProjectData (COA):
    - NO budžet field
    - NO ciljne_grupe, aktivnosti, rezultati fields
    - HAS planirani_koraci and ocekivani_uticaj fields

    Architecture: OneToOne with Application (type="COB")
    Story 3.5: COB Submission Processing
    """

    application = models.OneToOneField(
        Application,
        on_delete=models.CASCADE,
        related_name='initiative_data',
        verbose_name='Prijava'
    )

    # Initiative details (from Story 3-3, epics.md - Story 3.3)
    naslov = models.CharField(max_length=150, verbose_name='Naslov inicijative')
    kratak_opis = models.TextField(max_length=500, verbose_name='Kratak opis')
    problem = models.TextField(max_length=1500, verbose_name='Problem koji inicijativa rešava')
    cilj_inicijative = models.TextField(max_length=1500, verbose_name='Cilj inicijative')
    planirani_koraci = models.TextField(max_length=1500, verbose_name='Planirani koraci')
    ocekivani_uticaj = models.TextField(max_length=1500, verbose_name='Očekivani uticaj na zajednicu')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Datum kreiranja')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Datum izmene')

    class Meta:
        db_table = 'submissions_initiative_data'
        verbose_name = 'Podaci o inicijativi'
        verbose_name_plural = 'Podaci o inicijativama'
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['naslov']),
        ]

    def __str__(self):
        return f"Initiative: {self.naslov} ({self.application.reference_number})"


class FileMetadata(models.Model):
    """
    Metadata for uploaded files linked to applications.

    Tracks files that have been uploaded and linked to submitted applications.
    Works in conjunction with Story 2.9's file upload system.

    Fields:
        application: Link to Application (ForeignKey)
        file_type: Type of file (BUDGET, BIOGRAPHY, SUPPORT_LETTER)
        original_filename: Original name of uploaded file
        stored_filename: Unique filename in storage
        file_size: Size in bytes
        uploaded_at: Timestamp of upload
    """

    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='files',
        verbose_name='Prijava'
    )

    file_type = models.CharField(
        max_length=20,
        choices=FileType.CHOICES,
        verbose_name='Tip Fajla'
    )

    original_filename = models.CharField(
        max_length=255,
        verbose_name='Originalni Naziv'
    )

    stored_filename = models.CharField(
        max_length=255,
        verbose_name='Naziv u Skladištu'
    )

    file_size = models.IntegerField(
        verbose_name='Veličina Fajla',
        help_text='Bytes'
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Datum Upload-a'
    )

    class Meta:
        verbose_name = 'Metadata Fajla'
        verbose_name_plural = 'Metadata Fajlova'

    def __str__(self):
        """Return string representation of file metadata."""
        return f"{self.get_file_type_display()}: {self.original_filename}"


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
        choices=FileType.CHOICES,
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


class DraftMetadata(models.Model):
    """
    Server-side draft tracking model for GDPR-compliant 7-day retention.

    CRITICAL: This model stores ONLY metadata - NO actual form data.
    Form data remains ONLY in client localStorage.

    Purpose: Enable server-side GDPR 7-day auto-deletion policy
    without storing actual draft data.

    Privacy: NO form data stored - only existence metadata.

    Story 2.15: Draft Auto-Deletion Background Task
    """
    draft_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='Draft ID',
        help_text="Unique identifier for draft (matches localStorage key UUID)"
    )

    application_type = models.CharField(
        max_length=3,
        choices=[('COA', 'Projekat'), ('COB', 'Inicijativa')],
        verbose_name='Tip Prijave',
        help_text="Type of application (COA or COB)"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,  # ISSUE 7 FIX: Index verified for deletion query performance
        verbose_name='Kreirano',
        help_text="Timestamp when draft was first created"
    )

    last_updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Poslednje Ažurirano',
        help_text="Last time draft was updated (auto-save ping)"
    )

    class Meta:
        db_table = 'submissions_draft_metadata'
        verbose_name = 'Draft Metadata'
        verbose_name_plural = 'Draft Metadata Records'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at'], name='draft_created_idx'),
            models.Index(fields=['application_type'], name='draft_type_idx'),
        ]

    def __str__(self):
        """Return string representation of draft metadata."""
        return f"{self.application_type} Draft {self.draft_id} (created {self.created_at.strftime('%Y-%m-%d')})"

    def is_expired(self):
        """Check if draft is older than 7 days (GDPR retention)."""
        from datetime import timedelta
        # ISSUE 6 FIX: Defensive null check for created_at
        if not self.created_at:
            return True  # Treat drafts without created_at as expired
        expiry_date = timezone.now() - timedelta(days=7)
        return self.created_at < expiry_date
