# -*- coding: utf-8 -*-
"""
Django Admin configuration for submissions app.
Story 2.8: UploadedFile admin interface
Story 2.11: Added admin registrations for ReferenceNumberSequence, ProjectData, FileMetadata
Story 2.15: Added DraftMetadata admin interface
Story 4.1: Admin authentication and authorization - Application, Applicant admins enhanced
Story 4.2: Enhanced list view with query optimization, pagination, visual UX
"""
from django.contrib import admin
from django.utils.html import format_html, escape
from datetime import timedelta
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

# ISSUE 9 FIX: Constants for admin display configuration
RECENT_SUBMISSION_THRESHOLD = timedelta(hours=24)  # Submissions newer than this are highlighted


class EntityTypeFilter(admin.SimpleListFilter):
    """
    Story 4.2: Custom filter for entity type (fizičko/pravno lice).
    Allows filtering applications by applicant entity type.
    ISSUE 14 FIX: Explicit None handling for code clarity.

    ISSUE 2 NOTE: For optimal performance at scale (1000+ applicants), ensure
    Applicant.entity_type field has a database index. This is typically defined
    in the model with db_index=True. Current performance is acceptable for <1000 records.
    """
    title = 'Tip entiteta'
    parameter_name = 'entity_type'

    def lookups(self, request, model_admin):
        return (
            ('fizicko', 'Fizičko lice'),
            ('pravno', 'Pravno lice'),
        )

    def queryset(self, request, queryset):
        """Filter queryset by entity type or show all if None (default)."""
        if self.value() == 'fizicko':
            return queryset.filter(applicant__entity_type='fizicko')
        elif self.value() == 'pravno':
            return queryset.filter(applicant__entity_type='pravno')
        # ISSUE 14 FIX: Explicit None case - show all applications
        return queryset


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    """
    Django Admin interface for Application model.
    Story 4.1: Basic list view + search + filters
    Story 4.2: Enhanced list view with query optimization, pagination, visual UX
    Story 4.3: Enhanced detail view + inline editing (future)
    """

    list_display = (
        'reference_number',
        'get_applicant_name',
        'get_title',
        'get_application_type_display_serbian',  # Story 4.2: Serbian + icon
        'get_status_display_colored',            # Story 4.2: Color-coded status
        'get_submitted_at_display',              # Story 4.2: Highlight recent
    )

    list_filter = (
        'application_type',
        'status',
        'submitted_at',
        EntityTypeFilter,  # Story 4.2: Filter by fizičko/pravno lice
    )

    search_fields = (
        'reference_number',
        'applicant__first_name',
        'applicant__last_name',
        'applicant__organization_name',
        'applicant__email',
        'project_data__title',       # Story 4.2: Search COA project title
        'initiative_data__naslov',   # Story 4.2: Search COB initiative title
    )

    readonly_fields = (
        'reference_number',
        'application_type',
        'submitted_at',
        # Note: created_at field removed - Application model only has submitted_at
    )

    ordering = ['-submitted_at']  # Newest first

    # Story 4.2: Pagination (25 applications per page)
    list_per_page = 25
    list_max_show_all = 100

    # ISSUE 6 FIX: Use list_select_related for declarative query optimization
    # This complements get_queryset() but is more Django-idiomatic for simple cases
    list_select_related = ('applicant',)

    # BUGFIX: date_hierarchy disabled due to MySQL timezone issue
    # See: https://docs.djangoproject.com/en/5.2/ref/contrib/admin/#django.contrib.admin.ModelAdmin.date_hierarchy
    # To enable: Install MySQL timezone data first (see README.md)
    # date_hierarchy = 'submitted_at'

    def get_queryset(self, request):
        """
        Story 4.2: Optimize queryset with select_related to avoid N+1 queries.
        Prefetch project_data and initiative_data for get_title() method.
        NFR3: Admin panel loads in <3 seconds.
        """
        qs = super().get_queryset(request)
        qs = qs.select_related('applicant')  # Avoid extra queries for applicant data
        qs = qs.prefetch_related('project_data', 'initiative_data')  # Prefetch title data
        return qs

    def get_applicant_name(self, obj):
        """
        Story 4.2: Display applicant name with entity type icon.
        Icons: 👤 for fizičko lice, 🏢 for pravno lice
        """
        name = str(obj.applicant)  # Uses Applicant model's __str__ method
        entity_icon = '👤' if obj.applicant.entity_type == 'fizicko' else '🏢'
        return f"{entity_icon} {name}"
    get_applicant_name.short_description = 'Podnosilac'
    get_applicant_name.admin_order_field = 'applicant__first_name'  # Allow sorting

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

    def get_application_type_display_serbian(self, obj):
        """
        Story 4.2: Display application type in Serbian with icon.
        Icons: 📋 for COA (Projekat), 💡 for COB (Inicijativa)
        """
        if obj.application_type == 'COA':
            return '📋 Projekat'
        else:  # COB
            return '💡 Inicijativa'
    get_application_type_display_serbian.short_description = 'Tip prijave'
    get_application_type_display_serbian.admin_order_field = 'application_type'

    def get_status_display_colored(self, obj):
        """
        Story 4.2: Display status with color coding.
        Colors: gray (Podnet), yellow (Na pregledu), green (Odobren), red (Odbijen)
        ISSUE 11 FIX: Added ARIA labels for accessibility (screen reader support)
        """
        status_colors = {
            'submitted': '#6c757d',      # Gray
            'under_review': '#ffc107',   # Yellow
            'approved': '#28a745',       # Green
            'rejected': '#dc3545',       # Red
        }

        status_labels = {
            'submitted': 'Podnet',
            'under_review': 'Na pregledu',
            'approved': 'Odobren',
            'rejected': 'Odbijen',
        }

        color = status_colors.get(obj.status, '#6c757d')
        label = status_labels.get(obj.status, obj.status)

        return format_html(
            '<span style="color: {}; font-weight: bold;" aria-label="Status: {}">● {}</span>',
            color,
            escape(label),  # ISSUE 5 FIX: XSS protection with escape()
            escape(label)
        )
    get_status_display_colored.short_description = 'Status'
    get_status_display_colored.admin_order_field = 'status'

    def get_submitted_at_display(self, obj):
        """
        Story 4.2: Display submitted_at with highlighting for recent submissions (<24h).
        Recent submissions: 🆕 icon + blue bold text
        ISSUE 9 FIX: Uses RECENT_SUBMISSION_THRESHOLD constant
        ISSUE 11 FIX: Added ARIA label for accessibility
        """
        if not obj.submitted_at:
            return 'N/A'

        from django.utils import timezone

        now = timezone.now()
        time_diff = now - obj.submitted_at

        if time_diff < RECENT_SUBMISSION_THRESHOLD:
            # Recent submission: bold + blue color + ARIA label
            return format_html(
                '<span style="font-weight: bold; color: #007bff;" aria-label="Nova prijava ({})">🆕 {}</span>',
                obj.submitted_at.strftime('%Y-%m-%d %H:%M'),
                obj.submitted_at.strftime('%Y-%m-%d %H:%M')
            )
        else:
            return obj.submitted_at.strftime('%Y-%m-%d %H:%M')

    get_submitted_at_display.short_description = 'Datum podnošenja'
    get_submitted_at_display.admin_order_field = 'submitted_at'

    # Story 4.2: Load custom CSS for enhanced admin UX
    class Media:
        """
        ISSUE 13 FIX: Media class loads custom CSS for DOMOVIK design system.

        Loads admin_custom.css which applies:
        - DOMOVIK civic tech color palette (tirkizna #0EA5E9, koraljna #FF7A59)
        - Row hover effects for better UX
        - Reference number link styling
        - Filter sidebar enhancements

        ISSUE 4 NOTE: CSS file location is apps/submissions/static/admin/css/admin_custom.css
        This works because:
        1. STATICFILES_DIRS includes BASE_DIR / 'static' (global static)
        2. Django AppDirectoriesFinder searches app-level static dirs
        3. Path 'admin/css/admin_custom.css' resolves correctly in both dev and production
        4. Production: Run collectstatic before deployment
        """
        css = {
            'all': ('admin/css/admin_custom.css',)
        }

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
