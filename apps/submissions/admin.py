# -*- coding: utf-8 -*-
"""
Django Admin configuration for submissions app.
Story 2.8: UploadedFile admin interface
"""
from django.contrib import admin
from apps.submissions.models import Application, Applicant, UploadedFile


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
