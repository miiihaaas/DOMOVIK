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
        consent_*: Proof of the three consent checkboxes (Z11), see below
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

    # Z11 (2026-07-25): proof of consent (GDPR Art. 7(1) / ZZPL čl. 15 - the controller
    # must be able to DEMONSTRATE that consent was given). The three checkboxes were
    # validated at submit time and then thrown away, so there was nothing to show if an
    # applicant ever disputed it. Recorded now, together with when it happened and which
    # version of the policy the applicant actually agreed to - the text will change, and
    # "they accepted the policy" means nothing without knowing which one.
    # Applications submitted before Z11 keep False/NULL: that is the honest record, the
    # consent existed but was never captured.
    consent_privacy = models.BooleanField(
        default=False,
        verbose_name='Saglasnost - Politika privatnosti'
    )

    consent_terms = models.BooleanField(
        default=False,
        verbose_name='Saglasnost - Uslovi korišćenja'
    )

    consent_accuracy = models.BooleanField(
        default=False,
        verbose_name='Saglasnost - Tačnost podataka'
    )

    consent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Vreme davanja saglasnosti'
    )

    consent_policy_version = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Verzija politike',
        help_text='Verzija Politike privatnosti / Uslova korišćenja prihvaćena pri slanju'
    )

    consent_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name='IP adresa pri davanju saglasnosti'
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

    # Story 5.1: Renamed from JMBG to "Broj lične karte / ID broj"
    # Format: IDxxxxxx (ID + 6-7 digits)
    # Field name kept as 'jmbg' for backward compatibility
    jmbg = models.CharField(
        max_length=9,  # ID + 7 digits max
        blank=True,
        null=True,
        verbose_name='Broj lične karte / ID broj',
        help_text='Format: IDxxxxxx (npr. ID123456)'
    )

    # Pravno lice fields
    organization_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Naziv Organizacije'
    )

    # Story 5.1: Renamed from "Matični broj" to "Registracioni broj"
    # Format: Open alphanumeric (max 50 chars)
    # Field name kept as 'maticni_broj' for backward compatibility
    maticni_broj = models.CharField(
        max_length=50,  # Increased from 8 to 50 for alphanumeric format
        blank=True,
        null=True,
        verbose_name='Registracioni broj',
        help_text='Alfanumerički format (npr. REG-2024-ABC)'
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

    # Story 5.2: Project timeline dates
    datum_startovanja = models.DateField(
        null=True,
        blank=True,
        verbose_name='Datum startovanja',
        help_text='Planirani datum početka projekta'
    )

    datum_zavrsetka = models.DateField(
        null=True,
        blank=True,
        verbose_name='Datum završetka',
        help_text='Planirani datum završetka projekta'
    )

    class Meta:
        verbose_name = 'Podaci Projekta'
        verbose_name_plural = 'Podaci Projekata'

    def __str__(self):
        """Return string representation of project data."""
        return f"ProjectData: {self.title[:50]}"

    def clean(self):
        """
        Validate project data including date constraints.

        Story 5.2: Ensures datum_zavrsetka >= datum_startovanja
        """
        super().clean()

        # Validate date range if both dates are provided
        if self.datum_startovanja and self.datum_zavrsetka:
            if self.datum_zavrsetka < self.datum_startovanja:
                raise ValidationError({
                    'datum_zavrsetka': 'Datum završetka ne može biti pre datuma startovanja.'
                })


class InitiativeData(models.Model):
    """
    COB (Inicijativa) - Initiative-specific data.

    Story 3.5: COB Submission Processing
    Story 5.3: Added naziv_tima, date fields, totalni_budzet

    Fields added in Story 5.3:
    - naziv_tima: Team name (max 150 chars)
    - datum_startovanja: Project start date
    - datum_zavrsetka: Project end date
    - totalni_budzet: Total budget in EUR

    Architecture: OneToOne with Application (type="COB")
    """

    application = models.OneToOneField(
        Application,
        on_delete=models.CASCADE,
        related_name='initiative_data',
        verbose_name='Prijava'
    )

    # Story 5.3: Team name - FIRST field in Section II
    naziv_tima = models.CharField(
        max_length=150,
        verbose_name='Naziv tima',
        help_text='Ime tima koji podnosi inicijativu',
        blank=True,  # Allow blank for migration, will be required in form
        default=''
    )

    # Initiative details (from Story 3-3, epics.md - Story 3.3)
    naslov = models.CharField(max_length=150, verbose_name='Naslov inicijative')
    kratak_opis = models.TextField(max_length=500, verbose_name='Kratak opis')
    problem = models.TextField(max_length=1500, verbose_name='Problem koji inicijativa rešava')
    cilj_inicijative = models.TextField(max_length=1500, verbose_name='Cilj inicijative')
    # Story 5.3: Renamed verbose_name from "Planirani koraci" to "Planirane aktivnosti"
    planirani_koraci = models.TextField(max_length=1500, verbose_name='Planirane aktivnosti')
    ocekivani_uticaj = models.TextField(max_length=1500, verbose_name='Očekivani uticaj na zajednicu')

    # Story 5.3: Project timeline dates
    datum_startovanja = models.DateField(
        null=True,
        blank=True,
        verbose_name='Datum startovanja',
        help_text='Planirani datum početka inicijative'
    )

    datum_zavrsetka = models.DateField(
        null=True,
        blank=True,
        verbose_name='Datum završetka',
        help_text='Planirani datum završetka inicijative'
    )

    # Story 5.3: Total budget in EUR
    totalni_budzet = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Totalni budžet',
        help_text='Ukupan budžet u EUR'
    )

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

    def clean(self):
        """
        Validate initiative data including date constraints.

        Story 5.3: Ensures datum_zavrsetka >= datum_startovanja
        """
        super().clean()

        # Validate date range if both dates are provided
        if self.datum_startovanja and self.datum_zavrsetka:
            if self.datum_zavrsetka < self.datum_startovanja:
                raise ValidationError({
                    'datum_zavrsetka': 'Datum završetka ne može biti pre datuma startovanja.'
                })

        # Validate budget is non-negative
        if self.totalni_budzet is not None and self.totalni_budzet < 0:
            raise ValidationError({
                'totalni_budzet': 'Budžet mora biti pozitivan broj.'
            })


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


class AdminLog(models.Model):
    """
    Audit trail for admin panel and API actions.
    Story 4.6: Admin Activity Logging.

    Tracks all admin actions (views, downloads, status changes) for compliance
    and troubleshooting. Logs are read-only and retained for minimum 90 days
    (automatic cleanup via Celery periodic task).

    Fields:
        timestamp: When action occurred (auto-generated)
        user: Admin user who performed action
        action: Action type constant (e.g., 'viewed_application', 'changed_status')
        application: Application this action was performed on (optional)
        old_value: Previous value for changes (optional, e.g., old status)
        new_value: New value for changes (optional, e.g., new status)
        ip_address: IP address of admin user (supports IPv4 and IPv6)
        user_agent: Browser user agent string (truncated to 500 chars)

    Examples:
        >>> AdminLog.objects.create(
        ...     user=admin_user,
        ...     action='viewed_application',
        ...     application=app,
        ...     ip_address='192.168.1.1'
        ... )
        >>> AdminLog.objects.create(
        ...     user=admin_user,
        ...     action='changed_status',
        ...     application=app,
        ...     old_value='submitted',
        ...     new_value='approved'
        ... )
    """

    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='Vreme',
        help_text='When action was performed'
    )

    user = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='admin_logs',
        db_index=True,
        verbose_name='Korisnik',
        help_text='Admin user who performed the action'
    )

    action = models.CharField(
        max_length=50,
        db_index=True,
        verbose_name='Akcija',
        help_text="Action type (e.g., 'viewed_application', 'changed_status')"
    )

    application = models.ForeignKey(
        Application,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='admin_logs',
        verbose_name='Prijava',
        help_text='Application this action was performed on (if applicable)'
    )

    old_value = models.TextField(
        null=True,
        blank=True,
        verbose_name='Stara Vrednost',
        help_text='Previous value for changes (e.g., old status)'
    )

    new_value = models.TextField(
        null=True,
        blank=True,
        verbose_name='Nova Vrednost',
        help_text='New value for changes (e.g., new status)'
    )

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name='IP Adresa',
        help_text='IP address of admin user (IPv4 or IPv6)'
    )

    user_agent = models.TextField(
        null=True,
        blank=True,
        verbose_name='User Agent',
        help_text='Browser user agent string'
    )

    class Meta:
        db_table = 'admin_logs'
        ordering = ['-timestamp']
        verbose_name = 'Admin Log'
        verbose_name_plural = 'Admin Logs'
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['user']),
            models.Index(fields=['action']),
            models.Index(fields=['application']),
            # Performance optimization: Composite index for filtering by action + date
            # Enables efficient queries like: AdminLog.objects.filter(action='changed_status').order_by('-timestamp')
            models.Index(fields=['action', '-timestamp'], name='admin_logs_action_time_idx'),
        ]

    def __str__(self):
        """Return string representation of admin log entry."""
        if self.application:
            return f"{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')} - {self.user.username} - {self.action} - {self.application.reference_number}"
        return f"{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')} - {self.user.username} - {self.action}"


class ClanTima(models.Model):
    """
    Team member model for COA/COB applications.

    Story 5.1: Form Enhancements - Team Members

    Stores additional team members for an application.
    Each application can have multiple team members (minimum 1 row displayed).
    All fields are optional (blank=True) per requirements.

    Fields:
        application: ForeignKey to Application (one application can have multiple team members)
        ime_prezime: Full name (max 100 chars, optional)
        email: Email address (optional)
        telefon: Phone number (max 30 chars, optional)
    """

    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='clanovi_tima',
        verbose_name='Prijava',
        help_text='Application this team member belongs to'
    )

    ime_prezime = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Ime i prezime',
        help_text='Puno ime člana tima'
    )

    email = models.EmailField(
        blank=True,
        verbose_name='Email',
        help_text='Email adresa člana tima'
    )

    telefon = models.CharField(
        max_length=30,
        blank=True,
        verbose_name='Telefon',
        help_text='Broj telefona člana tima'
    )

    class Meta:
        db_table = 'submissions_clan_tima'
        verbose_name = 'Član tima'
        verbose_name_plural = 'Članovi tima'
        ordering = ['id']

    def __str__(self):
        """Return string representation of team member."""
        if self.ime_prezime:
            return f"{self.ime_prezime} ({self.application.reference_number})"
        return f"Član tima #{self.id} ({self.application.reference_number})"
