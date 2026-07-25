# -*- coding: utf-8 -*-
"""
Constants for submissions app.
Story 2.11: Application types and statuses
"""

# Version of the Politika privatnosti / Uslovi korišćenja an applicant accepts when
# submitting. Stored on every application (Z11) so it stays clear WHICH text was agreed
# to. BUMP THIS whenever templates/static_pages/*.html change in substance, and keep it
# equal to the "Poslednja izmena" line shown on those pages.
POLICY_VERSION = '2025-12'

# GDPR retention window for anything belonging to an unfinished application:
# draft metadata, and (Z8) uploaded files never linked to a submitted application.
# Must stay in sync with MAX_AGE in static/js/draft-manager.js.
DRAFT_RETENTION_DAYS = 7


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

    # COB file types (Story 3-5, Updated Story 5.4)
    BUDZET_INICIJATIVE = 'BUDZET_INICIJATIVE'  # Story 5.4: Renamed from OPIS_INICIJATIVE
    PISMO_PODRSKE = 'PISMO_PODRSKE'  # Story 5.4: Renamed from PISMO_NAMERE

    CHOICES = [
        (BUDGET, 'Budžet'),
        (BIOGRAPHY, 'Biografija'),
        (SUPPORT_LETTER, 'Pismo Podrške'),
        (BUDZET_INICIJATIVE, 'Budžet Inicijative'),  # Story 5.4
        (PISMO_PODRSKE, 'Pismo Podrške'),  # Story 5.4
    ]


# Story 4.4: File storage category folder mapping
# Maps FileMetadata.file_type values to filesystem subdirectories
# BUGFIX: Keys must match FileType constants (BUDGET, not BUDZET)
FILE_CATEGORY_FOLDERS = {
    'BUDGET': 'budgets',
    'BIOGRAPHY': 'biographies',
    'SUPPORT_LETTER': 'letters_of_support',
    # Story 5.4: Updated COB file categories
    'BUDZET_INICIJATIVE': 'initiative_budgets',  # Was: initiative_descriptions
    'PISMO_PODRSKE': 'letters_of_support_cob',  # Was: letters_of_intent
    # Z1 (2026-07-24): legacy COB categories from pre-5.4 submissions (still in DB)
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
