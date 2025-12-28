# -*- coding: utf-8 -*-
"""
Submission Processing Services for DOMOVIK
Story 2.11: Reference Number Generation & Submission Processing

This module provides services for:
1. Sequential reference number generation (COA-YYYY-NNN format)
2. Atomic submission processing with database transactions
3. File metadata linking
"""

from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from apps.submissions.models import (
    ReferenceNumberSequence,
    Application,
    Applicant,
    ProjectData,
    FileMetadata
)
from apps.submissions.validators import (
    validate_email,
    validate_phone,
    validate_jmbg,
    validate_maticni_broj
)
from apps.submissions.constants import ApplicationType, ApplicationStatus, EntityType
import logging

logger = logging.getLogger('domovik.submissions')


class ReferenceNumberService:
    """
    Service for generating sequential reference numbers.

    Generates unique reference numbers in format: COA-YYYY-NNN or COB-YYYY-NNN
    - YYYY: Current year (e.g., 2025)
    - NNN: Sequential number (001, 002, 003...)

    Features:
    - Thread-safe generation using database row locking (select_for_update)
    - Year-based reset (counter resets to 001 on January 1st)
    - No gaps in sequence (sequential numbering without missing numbers)
    """

    @staticmethod
    @transaction.atomic
    def generate_reference_number(application_type):
        """
        Generate sequential reference number in format: COA-YYYY-NNN.

        Uses database row-level locking to prevent race conditions and ensure
        unique, sequential numbers without gaps.

        Args:
            application_type (str): "COA" or "COB"

        Returns:
            str: Formatted reference number (e.g., "COA-2025-001")

        Raises:
            Exception: If database operation fails

        Example:
            >>> ReferenceNumberService.generate_reference_number("COA")
            'COA-2025-001'
            >>> ReferenceNumberService.generate_reference_number("COA")
            'COA-2025-002'
        """
        try:
            # Get current year
            current_year = timezone.now().year

            # Get or create sequence record with row-level locking
            # select_for_update() ensures thread-safe incrementing
            sequence, created = ReferenceNumberSequence.objects.select_for_update().get_or_create(
                year=current_year,
                application_type=application_type,
                defaults={'last_number': 0}
            )

            # Increment sequence number
            sequence.last_number += 1
            sequence.save()

            # Format reference number: COA-2025-001
            reference_number = f"{application_type}-{current_year}-{sequence.last_number:03d}"

            logger.info(f"Generated reference number: {reference_number}")
            return reference_number

        except Exception as e:
            logger.error(f"Failed to generate reference number for {application_type}: {str(e)}", exc_info=True)
            raise


@transaction.atomic(using='default', durable=True)
def process_submission(submission_data):
    """
    Process complete submission with atomic transaction.

    This function processes a complete COA/COB submission including:
    1. Reference number generation
    2. Applicant record creation
    3. Application record creation
    4. ProjectData record creation (COA only)
    5. FileMetadata records creation

    All operations are wrapped in a database transaction (@transaction.atomic).
    If any step fails, the entire transaction is rolled back (no partial data).

    Args:
        submission_data (dict): Complete submission data with structure:
            {
                'application_type': 'COA' or 'COB',
                'applicant': {
                    'entity_type': 'fizicko' or 'pravno',
                    'first_name': str,
                    'last_name': str,
                    'organization_name': str,
                    'address': str,
                    'email': str,
                    'phone': str,
                    'jmbg': str (optional),
                    'maticni_broj': str (optional)
                },
                'project': {
                    'title': str,
                    'short_description': str,
                    'problem': str,
                    'main_goal': str,
                    'specific_goals': str,
                    'target_groups': str,
                    'activities': str,
                    'results': str,
                    'total_budget': int
                },
                'files': [
                    {
                        'file_type': 'BUDGET' | 'BIOGRAPHY' | 'SUPPORT_LETTER',
                        'original_filename': str,
                        'stored_filename': str,
                        'file_size': int
                    },
                    ...
                ],
                'consent': {
                    'privacy': bool,
                    'terms': bool,
                    'accuracy': bool
                }
            }

    Returns:
        dict: Success response with reference number
            {'success': True, 'reference_number': 'COA-2025-001'}
        OR Error response
            {'success': False, 'error': 'Error message'}

    Example:
        >>> result = process_submission({
        ...     'application_type': 'COA',
        ...     'applicant': {...},
        ...     'project': {...},
        ...     'files': [...]
        ... })
        >>> print(result)
        {'success': True, 'reference_number': 'COA-2025-001'}
    """
    try:
        # Extract data from submission
        applicant_data = submission_data.get('applicant', {})
        project_data = submission_data.get('project', {})
        files_metadata = submission_data.get('files', [])
        application_type = submission_data.get('application_type', 'COA')

        # Step 0: Validate applicant data with backend validators
        validate_email(applicant_data.get('email'))
        validate_phone(applicant_data.get('phone'))

        # Validate JMBG for fizicko lice
        if applicant_data.get('entity_type') == EntityType.FIZICKO:
            validate_jmbg(applicant_data.get('jmbg'))

        # Validate maticni_broj for pravno lice
        if applicant_data.get('entity_type') == EntityType.PRAVNO:
            validate_maticni_broj(applicant_data.get('maticni_broj'))

        # Step 1: Generate reference number (thread-safe, sequential)
        reference_number = ReferenceNumberService.generate_reference_number(application_type)

        # Step 2: Create Application record
        application = Application.objects.create(
            reference_number=reference_number,
            application_type=application_type,
            status=ApplicationStatus.SUBMITTED,
            submitted_at=timezone.now()
        )

        # Step 3: Create Applicant record and link to Application
        applicant = Applicant.objects.create(
            application=application,
            entity_type=applicant_data.get('entity_type'),
            first_name=applicant_data.get('first_name', ''),
            last_name=applicant_data.get('last_name', ''),
            organization_name=applicant_data.get('organization_name', ''),
            address=applicant_data.get('address'),
            email=applicant_data.get('email'),
            phone=applicant_data.get('phone'),
            jmbg=applicant_data.get('jmbg'),
            maticni_broj=applicant_data.get('maticni_broj')
        )

        # Step 4: Create ProjectData record (COA only)
        if application_type == ApplicationType.COA and project_data:
            ProjectData.objects.create(
                application=application,
                title=project_data.get('title'),
                short_description=project_data.get('short_description'),
                problem=project_data.get('problem'),
                main_goal=project_data.get('main_goal'),
                specific_goals=project_data.get('specific_goals'),
                target_groups=project_data.get('target_groups'),
                activities=project_data.get('activities'),
                results=project_data.get('results'),
                total_budget=project_data.get('total_budget')
            )

        # Step 5: Create FileMetadata records for uploaded files
        if files_metadata:
            for file_meta in files_metadata:
                FileMetadata.objects.create(
                    application=application,
                    file_type=file_meta.get('file_type'),
                    original_filename=file_meta.get('original_filename'),
                    stored_filename=file_meta.get('stored_filename'),
                    file_size=file_meta.get('file_size')
                )

        # Log successful submission
        file_count = len(files_metadata) if files_metadata else 0
        logger.info(
            f"Submission SUCCESS: {reference_number} | "
            f"Applicant: {applicant.email} | "
            f"Type: {application_type} | "
            f"Files: {file_count}"
        )

        return {
            'success': True,
            'reference_number': reference_number
        }

    except Exception as e:
        # Log failure with full traceback
        logger.error(f"Submission FAILURE: {str(e)}", exc_info=True)

        # Return user-friendly error message (no stack trace)
        return {
            'success': False,
            'error': 'Greška pri čuvanju prijave. Molimo pokušajte ponovo.'
        }


# Export list for module
__all__ = [
    'ReferenceNumberService',
    'process_submission',
]
