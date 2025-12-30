# -*- coding: utf-8 -*-
"""
Constants for submissions app.
Story 2.11: Application types and statuses
"""


class ApplicationType:
    """Application type constants."""
    COA = 'COA'
    COB = 'COB'

    CHOICES = [
        (COA, 'Prijava za Projekat'),
        (COB, 'Prijava za Inicijativu'),
    ]


class ApplicationStatus:
    """Application status constants."""
    SUBMITTED = 'submitted'
    UNDER_REVIEW = 'under_review'
    APPROVED = 'approved'
    REJECTED = 'rejected'

    CHOICES = [
        (SUBMITTED, 'Podneto'),
        (UNDER_REVIEW, 'U Razmatranju'),
        (APPROVED, 'Odobreno'),
        (REJECTED, 'Odbijeno'),
    ]


class EntityType:
    """Applicant entity type constants."""
    FIZICKO = 'fizicko'
    PRAVNO = 'pravno'

    CHOICES = [
        (FIZICKO, 'Fizičko Lice'),
        (PRAVNO, 'Pravno Lice'),
    ]


class FileType:
    """File type/category constants."""
    # COA file types
    BUDGET = 'BUDGET'
    BIOGRAPHY = 'BIOGRAPHY'
    SUPPORT_LETTER = 'SUPPORT_LETTER'

    # COB file types (Story 3-5)
    OPIS_INICIJATIVE = 'OPIS_INICIJATIVE'
    PISMO_NAMERE = 'PISMO_NAMERE'

    CHOICES = [
        (BUDGET, 'Budžet'),
        (BIOGRAPHY, 'Biografija'),
        (SUPPORT_LETTER, 'Pismo Podrške'),
        (OPIS_INICIJATIVE, 'Opis Inicijative'),
        (PISMO_NAMERE, 'Pismo Namere'),
    ]


# Story 4.4: File storage category folder mapping
# Maps FileMetadata.file_type values to filesystem subdirectories
# BUGFIX: Keys must match FileType constants (BUDGET, not BUDZET)
FILE_CATEGORY_FOLDERS = {
    'BUDGET': 'budgets',
    'BIOGRAPHY': 'biographies',
    'SUPPORT_LETTER': 'letters_of_support',
    'OPIS_INICIJATIVE': 'initiative_descriptions',
    'PISMO_NAMERE': 'letters_of_intent',
}


# ============================================================================
# Admin Activity Logging - Action Types (Story 4.6)
# ============================================================================

# Django Admin actions
ADMIN_ACTION_VIEWED = 'viewed_application'
ADMIN_ACTION_DOWNLOADED_FILE = 'downloaded_file'
ADMIN_ACTION_DOWNLOADED_ALL = 'downloaded_all_files'
ADMIN_ACTION_STATUS_CHANGE = 'changed_status'

# API actions
ADMIN_ACTION_API_VIEWED = 'viewed_application_api'
ADMIN_ACTION_API_STATUS_CHANGE = 'changed_status_api'
ADMIN_ACTION_API_DOWNLOADED_FILE = 'downloaded_file_api'
ADMIN_ACTION_API_DOWNLOADED_ALL = 'downloaded_all_files_api'


# Export list
__all__ = [
    'ApplicationType',
    'ApplicationStatus',
    'EntityType',
    'FileType',
    'FILE_CATEGORY_FOLDERS',
    'ADMIN_ACTION_VIEWED',
    'ADMIN_ACTION_DOWNLOADED_FILE',
    'ADMIN_ACTION_DOWNLOADED_ALL',
    'ADMIN_ACTION_STATUS_CHANGE',
    'ADMIN_ACTION_API_VIEWED',
    'ADMIN_ACTION_API_STATUS_CHANGE',
    'ADMIN_ACTION_API_DOWNLOADED_FILE',
    'ADMIN_ACTION_API_DOWNLOADED_ALL',
]
