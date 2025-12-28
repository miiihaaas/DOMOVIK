# -*- coding: utf-8 -*-
"""
Django Admin configuration for submissions app.
Story 2.8: UploadedFile admin interface
Story 2.11: Added admin registrations for ReferenceNumberSequence, ProjectData, FileMetadata
"""
from django.contrib import admin
from apps.submissions.models import (
    Application,
    Applicant,
    UploadedFile,
    ReferenceNumberSequence,
    ProjectData,
    FileMetadata
)


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
    """
    list_display = ['title', 'application', 'total_budget', 'short_desc_preview']
    search_fields = ['title', 'short_description']
    readonly_fields = ['application']

    def short_desc_preview(self, obj):
        """Display truncated short description."""
        return obj.short_description[:100] + '...' if len(obj.short_description) > 100 else obj.short_description
    short_desc_preview.short_description = 'Kratak Opis'


@admin.register(FileMetadata)
class FileMetadataAdmin(admin.ModelAdmin):
    """
    Admin interface for FileMetadata model.
    Story 2.11: File metadata admin
    """
    list_display = ['original_filename', 'file_type', 'file_size_display', 'application', 'uploaded_at']
    list_filter = ['file_type', 'uploaded_at']
    search_fields = ['original_filename', 'stored_filename']
    readonly_fields = ['uploaded_at']

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
