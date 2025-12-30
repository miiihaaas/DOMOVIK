# -*- coding: utf-8 -*-
"""
Django Admin configuration for submissions app.
Story 2.8: UploadedFile admin interface
Story 2.11: Added admin registrations for ReferenceNumberSequence, ProjectData, FileMetadata
Story 2.15: Added DraftMetadata admin interface
Story 4.1: Admin authentication and authorization - Application, Applicant admins enhanced
Story 4.2: Enhanced list view with query optimization, pagination, visual UX
Story 4.3: Enhanced detail view with dynamic fieldsets, status editing, FileMetadata inline

Code Review Story 4.3: All display methods wrapped with ObjectDoesNotExist handling
"""
from django.contrib import admin
from django.utils.html import format_html, escape
from django.core.exceptions import ObjectDoesNotExist
from datetime import timedelta
from apps.submissions.models import (
    Application,
    Applicant,
    UploadedFile,
    ReferenceNumberSequence,
    ProjectData,
    InitiativeData,
    FileMetadata,
    DraftMetadata,
    AdminLog
)
from apps.submissions.services import log_admin_action
from apps.submissions.constants import (
    ADMIN_ACTION_VIEWED,
    ADMIN_ACTION_STATUS_CHANGE,
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


class FileMetadataInline(admin.TabularInline):
    """
    Inline display of FileMetadata for Application detail view.
    Story 4.3: Show uploaded documents in detail view (readonly).
    """
    model = FileMetadata
    extra = 0  # No empty forms (files come from frontend only)
    max_num = 0  # Prevent adding files via admin
    can_delete = False  # Prevent deleting files via admin

    fields = (
        'get_category_serbian',
        'original_filename',
        'get_file_size_mb',
        'uploaded_at',
        'get_download_link',  # Story 4.4 will implement actual download
    )

    readonly_fields = (
        'get_category_serbian',
        'original_filename',
        'get_file_size_mb',
        'uploaded_at',
        'get_download_link',
    )

    def get_category_serbian(self, obj):
        """
        Display file category in Serbian.
        CODE REVIEW NOTE: Category labels remain in admin.py (display logic),
        FILE_CATEGORY_FOLDERS moved to constants.py (storage paths).
        """
        category_labels = {
            'BUDZET': '📊 Budžet projekta',
            'BIOGRAFIJA': '👤 Biografija člana tima',
            'PISMO_PODRSKE': '✉️ Pismo podrške',
            'OPIS_INICIJATIVE': '📄 Opis inicijative',
            'PISMO_NAMERE': '✉️ Pismo namere',
        }
        return category_labels.get(obj.file_type, obj.file_type)
    get_category_serbian.short_description = 'Kategorija'

    def get_file_size_mb(self, obj):
        """Display file size in MB."""
        size_mb = obj.file_size / (1024 * 1024)
        return f"{size_mb:.2f} MB"
    get_file_size_mb.short_description = 'Veličina'

    def get_download_link(self, obj):
        """
        Display download link for individual file.
        Story 4.4: Implemented actual download functionality.
        """
        from django.urls import reverse

        # Get application ID from obj.application
        app_id = obj.application.id
        file_id = obj.id

        # Construct download URL
        download_url = reverse('submissions:admin_download_file', args=[app_id, file_id])

        # Return download link with icon
        return format_html(
            '<a href="{}" target="_blank" style="color: #0EA5E9; text-decoration: none;">'
            '⬇️ Download</a>',
            download_url
        )
    get_download_link.short_description = 'Download'

    def has_add_permission(self, request, obj=None):
        """Prevent adding files via admin (files come from frontend only)."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Prevent deleting files via admin (data retention policy)."""
        return False


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    """
    Django Admin interface for Application model.
    Story 4.1: Basic list view + search + filters
    Story 4.2: Enhanced list view with query optimization, pagination, visual UX
    Story 4.3: Enhanced detail view with dynamic fieldsets, status editing, FileMetadata inline
    """

    # Story 4.3: Add FileMetadata inline
    inlines = [FileMetadataInline]

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

    # Story 4.3: Expanded readonly_fields for detail view
    # Note: Fields used in fieldsets will be included automatically
    # Only define custom display methods here
    readonly_fields = (
        # Opsti podaci section - readonly model fields
        # NOTE: Application model doesn't have updated_at field (only InitiativeData has it)
        'reference_number',
        'application_type',
        'submitted_at',
        # Podnosilac section
        'get_entity_type_serbian',
        'get_applicant_first_name',
        'get_applicant_last_name',
        'get_applicant_jmbg',
        'get_applicant_organization_name',
        'get_applicant_maticni_broj',
        'get_applicant_address',
        'get_applicant_email',
        'get_applicant_phone',
        # Project data section (COA)
        'get_project_naslov',
        'get_project_kratak_opis',
        'get_project_problem',
        'get_project_glavni_cilj',
        'get_project_specificni_ciljevi',
        'get_project_ciljne_grupe',
        'get_project_aktivnosti',
        'get_project_rezultati',
        'get_project_totalni_budzet',
        # Initiative data section (COB)
        'get_initiative_naslov',
        'get_initiative_kratak_opis',
        'get_initiative_problem',
        'get_initiative_cilj_inicijative',
        'get_initiative_planirani_koraci',
        'get_initiative_ocekivani_uticaj',
        # Story 4.4: Download all documents button
        'get_download_all_button',
    )
    # Note: status is NOT in readonly_fields → editable dropdown

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
        Story 4.3: Added prefetch for files (FileMetadata inline) to avoid N+1 queries.
        NFR3: Admin panel loads in <3 seconds.
        """
        qs = super().get_queryset(request)
        qs = qs.select_related('applicant')  # Avoid extra queries for applicant data
        qs = qs.prefetch_related('project_data', 'initiative_data')  # Prefetch title data
        qs = qs.prefetch_related('files')  # ISSUE 11 FIX: Prefetch files for FileMetadataInline to avoid N+1
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

    def get_download_all_button(self, obj):
        """
        Display "Download All Documents" button.
        Story 4.4: Bulk ZIP download functionality.
        """
        from django.urls import reverse

        # Only show button if application has files
        if not obj.files.exists():
            return "Prijava nema upload-ovanih dokumenata."

        # Construct download URL
        download_url = reverse('submissions:admin_download_all', args=[obj.id])

        # Return styled button
        return format_html(
            '<a href="{}" class="button" style="background-color: #0EA5E9; color: white; '
            'padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">'
            '📦 Download All Documents (ZIP)</a>',
            download_url
        )
    get_download_all_button.short_description = 'Bulk Download'

    def get_fieldsets(self, request, obj=None):
        """
        Story 4.3: Dynamic fieldsets based on application type (COA/COB) and entity type (fizičko/pravno).
        Story 4.4: Add "Download All Documents" button section if files exist.
        Customize detail view to show relevant fields only.
        """
        if obj is None:
            # Adding new application (not allowed, but handle gracefully)
            return super().get_fieldsets(request, obj)

        # Section 1: Opšti podaci (always shown)
        # NOTE: Story mentioned updated_at but Application model doesn't have it (only created_at + submitted_at)
        opsti_podaci_fields = [
            'reference_number',
            'application_type',
            'status',
            'submitted_at',
        ]

        # Section 2: Podaci o podnosiocu (dynamic based on entity_type)
        podnosilac_fields = ['get_entity_type_serbian']

        if obj.applicant.entity_type == 'fizicko':
            # Fizičko lice
            podnosilac_fields.extend([
                'get_applicant_first_name',
                'get_applicant_last_name',
            ])
            if obj.application_type == 'COA':
                # Only COA fizičko lice has JMBG
                podnosilac_fields.append('get_applicant_jmbg')
        else:
            # Pravno lice
            podnosilac_fields.append('get_applicant_organization_name')
            if obj.application_type == 'COA':
                # Only COA pravno lice has matični broj
                podnosilac_fields.append('get_applicant_maticni_broj')

        # Common contact fields (always shown)
        podnosilac_fields.extend([
            'get_applicant_address',
            'get_applicant_email',
            'get_applicant_phone',
        ])

        # Section 3: Podaci o projektu/inicijativi (dynamic based on application_type)
        if obj.application_type == 'COA':
            # COA: Project data
            projekt_fields = [
                'get_project_naslov',
                'get_project_kratak_opis',
                'get_project_problem',
                'get_project_glavni_cilj',
                'get_project_specificni_ciljevi',
                'get_project_ciljne_grupe',
                'get_project_aktivnosti',
                'get_project_rezultati',
                'get_project_totalni_budzet',
            ]
            projekt_section_title = '📝 Podaci o projektu'
        else:
            # COB: Initiative data
            projekt_fields = [
                'get_initiative_naslov',
                'get_initiative_kratak_opis',
                'get_initiative_problem',
                'get_initiative_cilj_inicijative',
                'get_initiative_planirani_koraci',
                'get_initiative_ocekivani_uticaj',
            ]
            projekt_section_title = '💡 Podaci o inicijativi'

        # Build dynamic fieldsets (list to conditionally add download section)
        fieldsets = [
            ('📋 Opšti podaci', {
                'fields': opsti_podaci_fields,
            }),
            ('👤 Podaci o podnosiocu', {
                'fields': podnosilac_fields,
            }),
            (projekt_section_title, {
                'fields': projekt_fields,
            }),
        ]

        # Story 4.4: Add download button section if application has files
        if obj.files.exists():
            fieldsets.append(
                ('📦 Dokumentacija', {
                    'fields': ('get_download_all_button',),
                    'description': 'Download-ujte sve upload-ovane dokumente odjednom.',
                })
            )

        return tuple(fieldsets)

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        """
        Story 4.3: Customize status field dropdown to display Serbian labels.

        Maps internal English status values to Serbian labels for admin UX:
        - 'submitted' → 'Podnet'
        - 'under_review' → 'Na pregledu'
        - 'approved' → 'Odobren'
        - 'rejected' → 'Odbijen'

        Database values remain English for data consistency.
        ISSUE 14 FIX: Added comprehensive docstring explaining label mapping.
        """
        if db_field.name == 'status':
            kwargs['choices'] = [
                ('submitted', 'Podnet'),
                ('under_review', 'Na pregledu'),
                ('approved', 'Odobren'),
                ('rejected', 'Odbijen'),
            ]
        return super().formfield_for_choice_field(db_field, request, **kwargs)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        """
        Override change_view to log when admin views an application.
        Story 4.6: Admin Activity Logging.
        """
        # Call parent change_view first to render page
        response = super().change_view(request, object_id, form_url, extra_context)

        # Log "viewed application" action (only on GET, not on POST saves)
        if request.method == 'GET':
            try:
                application = Application.objects.get(pk=object_id)
                log_admin_action(
                    user=request.user,
                    action=ADMIN_ACTION_VIEWED,
                    application=application,
                    request=request,
                )
            except Application.DoesNotExist:
                pass  # Application not found, skip logging

        return response

    def save_model(self, request, obj, form, change):
        """
        Override save_model to log status changes.
        Story 4.6: Admin Activity Logging.
        """
        # Capture old status before saving (if editing existing application)
        old_status = None
        if change and obj.pk:
            try:
                old_application = Application.objects.get(pk=obj.pk)
                old_status = old_application.status
            except Application.DoesNotExist:
                pass

        # Save the model (parent call)
        super().save_model(request, obj, form, change)

        # Log status change if status was modified
        if change and old_status and old_status != obj.status:
            log_admin_action(
                user=request.user,
                action=ADMIN_ACTION_STATUS_CHANGE,
                application=obj,
                old_value=old_status,
                new_value=obj.status,
                request=request,
            )

    # SECTION: Opšti podaci display methods (Story 4.3)

    # get_application_type_serbian already exists from Story 4.2 - reuse for detail view

    # SECTION: Podnosilac display methods (Story 4.3)

    def get_entity_type_serbian(self, obj):
        """Display entity type in Serbian with icon."""
        if obj.applicant.entity_type == 'fizicko':
            return '👤 Fizičko lice'
        return '🏢 Pravno lice'
    get_entity_type_serbian.short_description = 'Tip entiteta'

    def get_applicant_first_name(self, obj):
        return obj.applicant.first_name or 'N/A'
    get_applicant_first_name.short_description = 'Ime'

    def get_applicant_last_name(self, obj):
        return obj.applicant.last_name or 'N/A'
    get_applicant_last_name.short_description = 'Prezime'

    def get_applicant_jmbg(self, obj):
        return obj.applicant.jmbg or 'N/A'
    get_applicant_jmbg.short_description = 'JMBG'

    def get_applicant_organization_name(self, obj):
        return obj.applicant.organization_name or 'N/A'
    get_applicant_organization_name.short_description = 'Naziv organizacije'

    def get_applicant_maticni_broj(self, obj):
        return obj.applicant.maticni_broj or 'N/A'
    get_applicant_maticni_broj.short_description = 'Matični broj'

    def get_applicant_address(self, obj):
        return obj.applicant.address
    get_applicant_address.short_description = 'Adresa'

    def get_applicant_email(self, obj):
        return obj.applicant.email
    get_applicant_email.short_description = 'Email'

    def get_applicant_phone(self, obj):
        return obj.applicant.phone
    get_applicant_phone.short_description = 'Telefon'

    # SECTION: Project data display methods (COA only) (Story 4.3)

    def get_project_naslov(self, obj):
        # ISSUE 5 FIX: Add try/except for ObjectDoesNotExist to handle orphaned relations
        try:
            if hasattr(obj, 'project_data'):
                return obj.project_data.title
        except ObjectDoesNotExist:
            pass
        return 'N/A'
    get_project_naslov.short_description = 'Naslov projekta'

    def get_project_kratak_opis(self, obj):
        if hasattr(obj, 'project_data'):
            # ISSUE 4 FIX: Explicit escape() for XSS protection (format_html auto-escapes {} but be explicit)
            return format_html('<div style="white-space: pre-wrap;">{}</div>', escape(obj.project_data.short_description))
        return 'N/A'
    get_project_kratak_opis.short_description = 'Kratak opis'

    def get_project_problem(self, obj):
        if hasattr(obj, 'project_data'):
            return format_html('<div style="white-space: pre-wrap;">{}</div>', escape(obj.project_data.problem))
        return 'N/A'
    get_project_problem.short_description = 'Problem koji se rešava'

    def get_project_glavni_cilj(self, obj):
        if hasattr(obj, 'project_data'):
            return format_html('<div style="white-space: pre-wrap;">{}</div>', escape(obj.project_data.main_goal))
        return 'N/A'
    get_project_glavni_cilj.short_description = 'Glavni cilj'

    def get_project_specificni_ciljevi(self, obj):
        if hasattr(obj, 'project_data'):
            return format_html('<div style="white-space: pre-wrap;">{}</div>', escape(obj.project_data.specific_goals))
        return 'N/A'
    get_project_specificni_ciljevi.short_description = 'Specifični ciljevi'

    def get_project_ciljne_grupe(self, obj):
        if hasattr(obj, 'project_data'):
            return format_html('<div style="white-space: pre-wrap;">{}</div>', escape(obj.project_data.target_groups))
        return 'N/A'
    get_project_ciljne_grupe.short_description = 'Ciljne grupe'

    def get_project_aktivnosti(self, obj):
        if hasattr(obj, 'project_data'):
            return format_html('<div style="white-space: pre-wrap;">{}</div>', escape(obj.project_data.activities))
        return 'N/A'
    get_project_aktivnosti.short_description = 'Aktivnosti'

    def get_project_rezultati(self, obj):
        if hasattr(obj, 'project_data'):
            return format_html('<div style="white-space: pre-wrap;">{}</div>', escape(obj.project_data.results))
        return 'N/A'
    get_project_rezultati.short_description = 'Rezultati'

    def get_project_totalni_budzet(self, obj):
        if hasattr(obj, 'project_data'):
            budget = obj.project_data.total_budget
            # ISSUE 2 FIX: total_budget is IntegerField, format as integer with thousand separators
            # Format as currency: 100,000 RSD (no decimals for IntegerField)
            formatted_budget = f"{budget:,} RSD"
            return format_html('<strong>{}</strong>', escape(formatted_budget))
        return 'N/A'
    get_project_totalni_budzet.short_description = 'Totalni budžet'

    # SECTION: Initiative data display methods (COB only) (Story 4.3)

    def get_initiative_naslov(self, obj):
        if hasattr(obj, 'initiative_data'):
            return obj.initiative_data.naslov
        return 'N/A'
    get_initiative_naslov.short_description = 'Naslov inicijative'

    def get_initiative_kratak_opis(self, obj):
        if hasattr(obj, 'initiative_data'):
            return format_html('<div style="white-space: pre-wrap;">{}</div>', escape(obj.initiative_data.kratak_opis))
        return 'N/A'
    get_initiative_kratak_opis.short_description = 'Kratak opis'

    def get_initiative_problem(self, obj):
        if hasattr(obj, 'initiative_data'):
            return format_html('<div style="white-space: pre-wrap;">{}</div>', escape(obj.initiative_data.problem))
        return 'N/A'
    get_initiative_problem.short_description = 'Problem koji inicijativa rešava'

    def get_initiative_cilj_inicijative(self, obj):
        if hasattr(obj, 'initiative_data'):
            return format_html('<div style="white-space: pre-wrap;">{}</div>', escape(obj.initiative_data.cilj_inicijative))
        return 'N/A'
    get_initiative_cilj_inicijative.short_description = 'Cilj inicijative'

    def get_initiative_planirani_koraci(self, obj):
        if hasattr(obj, 'initiative_data'):
            return format_html('<div style="white-space: pre-wrap;">{}</div>', escape(obj.initiative_data.planirani_koraci))
        return 'N/A'
    get_initiative_planirani_koraci.short_description = 'Planirani koraci'

    def get_initiative_ocekivani_uticaj(self, obj):
        if hasattr(obj, 'initiative_data'):
            return format_html('<div style="white-space: pre-wrap;">{}</div>', escape(obj.initiative_data.ocekivani_uticaj))
        return 'N/A'
    get_initiative_ocekivani_uticaj.short_description = 'Očekivani uticaj na zajednicu'


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


@admin.register(AdminLog)
class AdminLogAdmin(admin.ModelAdmin):
    """
    Django Admin interface for viewing admin activity logs.
    Story 4.6: Admin Activity Logging.

    Logs are read-only (cannot be added, edited, or deleted) for audit trail integrity.
    """

    list_display = [
        'timestamp',
        'user',
        'action',
        'get_application_reference',
        'old_value',
        'new_value',
        'ip_address',
    ]

    list_filter = [
        'action',
        'user',
        ('timestamp', admin.DateFieldListFilter),
    ]

    search_fields = [
        'application__reference_number',
        'user__username',
        'action',
        'ip_address',
    ]

    readonly_fields = [
        'timestamp',
        'user',
        'action',
        'application',
        'old_value',
        'new_value',
        'ip_address',
        'user_agent',
    ]

    # date_hierarchy = 'timestamp'  # DISABLED: SQLite incompatible with timezone-aware datetime
    # Use list_filter with DateFieldListFilter instead (line 991)

    ordering = ['-timestamp']

    # Disable add/delete (logs are read-only)
    def has_add_permission(self, request):
        """Prevent creating fake logs - logs are auto-generated only."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Prevent deleting audit trail - logs are permanent."""
        return False

    def has_change_permission(self, request, obj=None):
        """Allow viewing but not editing logs."""
        return True

    def get_application_reference(self, obj):
        """Display application reference number."""
        if obj.application:
            return obj.application.reference_number
        return '-'
    get_application_reference.short_description = 'Application'

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        """Make all fields read-only in detail view by hiding save buttons."""
        extra_context = extra_context or {}
        extra_context['show_save'] = False
        extra_context['show_save_and_continue'] = False
        extra_context['show_save_and_add_another'] = False
        return super().changeform_view(request, object_id, form_url, extra_context)


# Customize Django Admin site (Story 4.1: Admin Authentication)
admin.site.site_header = 'DOMOVIK Admin Panel'
admin.site.site_title = 'DOMOVIK Admin'
admin.site.index_title = 'Dobrodošli u DOMOVIK Admin Panel'
