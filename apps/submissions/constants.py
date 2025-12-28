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
    BUDGET = 'BUDGET'
    BIOGRAPHY = 'BIOGRAPHY'
    SUPPORT_LETTER = 'SUPPORT_LETTER'

    CHOICES = [
        (BUDGET, 'Budžet'),
        (BIOGRAPHY, 'Biografija'),
        (SUPPORT_LETTER, 'Pismo Podrške'),
    ]


# Export list
__all__ = [
    'ApplicationType',
    'ApplicationStatus',
    'EntityType',
    'FileType',
]
