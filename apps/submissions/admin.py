# -*- coding: utf-8 -*-
"""
Django Admin configuration for submissions app.
Story 2.8: UploadedFile admin interface
Story 2.11: Added admin registrations for ReferenceNumberSequence, ProjectData, FileMetadata
Story 2.15: Added DraftMetadata admin interface
Story 4.1: Admin authentication and authorization - Application, Applicant admins enhanced
"""
from django.contrib import admin
from django.utils.html import format_html
from apps.submissions.models import (
    Application,
    Applicant,
    UploadedFile,
    ReferenceNumberSequence,
    ProjectData,
    InitiativeData,
    FileMetadata,
    DraftMetadata
)


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    """
    Django Admin interface for Application model.
    Story 4.1: Basic list view + search + filters
    Story 4.3: Enhanced detail view + inline editing (future)
    """

    list_display = (
        'reference_number',
        'get_applicant_name',
        'get_title',
        'application_type',
        'status',
        'submitted_at',
    )

    list_filter = (
        'application_type',
        'status',
        'submitted_at',
    )

    search_fields = (
        'reference_number',
        'applicant__first_name',
        'applicant__last_name',
        'applicant__organization_name',
        'applicant__email',
    )

    readonly_fields = (
        'reference_number',
        'application_type',
        'submitted_at',
        'created_at',
    )

    ordering = ['-submitted_at']  # Newest first

    # BUGFIX: date_hierarchy disabled due to MySQL timezone issue
    # See: https://docs.djangoproject.com/en/5.2/ref/contrib/admin/#django.contrib.admin.ModelAdmin.date_hierarchy
    # To enable: Install MySQL timezone data first (see README.md)
    # date_hierarchy = 'submitted_at'

    def get_applicant_name(self, obj):
        """Display applicant name (fizičko full name or pravno organization name)."""
        return str(obj.applicant)  # Uses Applicant model's __str__ method
    get_applicant_name.short_description = 'Podnosilac'

    def get_title(self, obj):
        """Display project or initiative title."""
        from django.core.exceptions import ObjectDoesNotExist
        try:
            if obj.application_type == 'COA':
                return obj.project_data.title if hasattr(obj, 'project_data') else 'N/A'
            else:  # COB
                return obj.initiative_data.naslov if hasattr(obj, 'initiative_data') else 'N/A'
        except (AttributeError, ObjectDoesNotExist):
            return 'N/A'
    get_title.short_description = 'Naslov'

    def has_add_permission(self, request):
        """Disable adding applications via admin (submissions come from frontend only)."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Disable deleting applications via admin (data retention policy)."""
        return False


@admin.register(Applicant)
class ApplicantAdmin(admin.ModelAdmin):
    """
    Applicant model admin (readonly).
    Story 4.1: Admin authentication - Applicant viewing
    """
    list_display = (
        '__str__',  # Uses model's __str__ method which calls get_full_name logic
        'entity_type',
        'email',
        'phone',
    )

    list_filter = ('entity_type',)

    search_fields = (
        'first_name',
        'last_name',
        'organization_name',
        'email',
        'jmbg',
        'maticni_broj',
    )

    # ISSUE 12 FIX: Standardized to static readonly_fields (simpler, matches story spec)
    readonly_fields = [
        'application', 'entity_type', 'first_name', 'last_name', 'jmbg',
        'organization_name', 'maticni_broj', 'address', 'email', 'phone'
    ]

    def has_add_permission(self, request):
        """Disable adding applicants via admin (created from frontend submissions)."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Disable deleting applicants via admin (data retention policy)."""
        return False


@admin.register(ReferenceNumberSequence)
class ReferenceNumberSequenceAdmin(admin.ModelAdmin):
    """
    Admin interface for ReferenceNumberSequence model.
    Story 2.11: Reference number tracking
    """
    list_display = ['year', 'application_type', 'last_number', 'formatted_next']
    list_filter = ['year', 'application_type']
    search_fields = ['year']
    readonly_fields = ['last_number']

    def formatted_next(self, obj):
        """Display next reference number to be generated."""
        next_num = obj.last_number + 1
        return f"{obj.application_type}-{obj.year}-{next_num:03d}"
    formatted_next.short_description = 'Sledeći Broj'


@admin.register(ProjectData)
class ProjectDataAdmin(admin.ModelAdmin):
    """
    Admin interface for ProjectData model.
    Story 2.11: Project data admin
    Story 4.1: Made readonly for data integrity
    """
    list_display = ['title', 'get_reference_number', 'total_budget']
    search_fields = ['title', 'short_description']

    # ISSUE 12 FIX: Standardized to static readonly_fields
    readonly_fields = [
        'application', 'title', 'short_description', 'problem', 'main_goal',
        'specific_goals', 'target_groups', 'activities', 'results', 'total_budget'
    ]

    def get_reference_number(self, obj):
        """Display application reference number."""
        return obj.application.reference_number
    get_reference_number.short_description = 'Referentni broj'

    def has_add_permission(self, request):
        """Disable adding project data via admin (created from frontend submissions)."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Disable deleting project data via admin (data retention policy)."""
        return False


@admin.register(InitiativeData)
class InitiativeDataAdmin(admin.ModelAdmin):
    """
    Admin interface for InitiativeData model.
    Story 3.5: COB initiative data admin
    Story 4.1: Made readonly for data integrity
    """
    list_display = ['naslov', 'get_reference_number']
    search_fields = ['naslov', 'kratak_opis']

    # ISSUE 12 FIX: Standardized to static readonly_fields
    readonly_fields = [
        'application', 'naslov', 'kratak_opis', 'problem',
        'cilj_inicijative', 'planirani_koraci', 'ocekivani_uticaj',
        'created_at', 'updated_at'
    ]

    def get_reference_number(self, obj):
        """Display application reference number."""
        return obj.application.reference_number
    get_reference_number.short_description = 'Referentni broj'

    def has_add_permission(self, request):
        """Disable adding initiative data via admin (created from frontend submissions)."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Disable deleting initiative data via admin (data retention policy)."""
        return False


@admin.register(FileMetadata)
class FileMetadataAdmin(admin.ModelAdmin):
    """
    Admin interface for FileMetadata model.
    Story 2.11: File metadata admin
    Story 4.1: Made readonly for data integrity
    """
    list_display = ['original_filename', 'file_type', 'get_reference_number', 'file_size_mb', 'uploaded_at']
    list_filter = ['file_type', 'uploaded_at']
    search_fields = ['original_filename']

    # ISSUE 12 FIX: Standardized to static readonly_fields
    readonly_fields = [
        'application', 'file_type', 'original_filename', 'stored_filename',
        'file_size', 'uploaded_at'
    ]

    def get_reference_number(self, obj):
        """Display application reference number."""
        return obj.application.reference_number
    get_reference_number.short_description = 'Referentni broj'

    def file_size_mb(self, obj):
        """Display file size in MB."""
        return f"{obj.file_size / (1024 * 1024):.2f} MB"
    file_size_mb.short_description = 'Veličina'

    def has_add_permission(self, request):
        """Disable adding file metadata via admin (created from frontend uploads)."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Disable deleting file metadata via admin (data retention policy)."""
        return False


@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    """
    Admin interface for UploadedFile model.
    Story 2.8: File upload infrastructure admin
    """
    list_display = [
        'original_filename',
        'file_type',
        'file_size_display',
        'category',
        'upload_date',
        'uploaded_by_session',
        'application',
        'is_deleted'
    ]

    list_filter = [
        'file_type',
        'category',
        'upload_date',
        'is_deleted'
    ]

    search_fields = [
        'original_filename',
        'uploaded_by_session',
        'stored_filename'
    ]

    readonly_fields = [
        'upload_date',
        'stored_filename',
        'mime_type',
        'file_size'
    ]

    def file_size_display(self, obj):
        """Display file size in human-readable format (KB or MB)."""
        size_bytes = obj.file_size
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.2f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.2f} MB"

    file_size_display.short_description = 'Veličina Fajla'


@admin.register(DraftMetadata)
class DraftMetadataAdmin(admin.ModelAdmin):
    """
    Admin interface for DraftMetadata model.
    Story 2.15: Draft auto-deletion background task
    """
    list_display = [
        'draft_id',
        'application_type',
        'created_at',
        'last_updated_at',
        'age_in_days',
        'is_expired'
    ]

    list_filter = [
        'application_type',
        'created_at'
    ]

    search_fields = [
        'draft_id'
    ]

    readonly_fields = [
        'draft_id',
        'created_at',
        'last_updated_at',
        'age_in_days',
        'is_expired'
    ]

    def age_in_days(self, obj):
        """Display draft age in days."""
        from django.utils import timezone
        age = timezone.now() - obj.created_at
        return f"{age.days} days"
    age_in_days.short_description = 'Starost (dana)'

    def get_readonly_fields(self, request, obj=None):
        """Make all fields readonly in admin (metadata is auto-managed)."""
        if obj:
            return self.readonly_fields
        return []


# Customize Django Admin site (Story 4.1: Admin Authentication)
admin.site.site_header = 'DOMOVIK Admin Panel'
admin.site.site_title = 'DOMOVIK Admin'
admin.site.index_title = 'Dobrodošli u DOMOVIK Admin Panel'
