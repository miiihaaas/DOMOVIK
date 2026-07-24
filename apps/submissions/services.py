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
from django.conf import settings
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
    validate_registracioni_broj
)
from apps.submissions.constants import ApplicationType, ApplicationStatus, EntityType, FILE_CATEGORY_FOLDERS
import os
import logging

logger = logging.getLogger('domovik.submissions')


def resolve_file_on_disk(file_metadata):
    """
    Return the absolute on-disk path for a FileMetadata's file, or None if not found.

    Z1 (2026-07-24): single source of truth for locating an uploaded file, shared by
    the admin download views and the fix_file_metadata repair command. Search order:

      1. Linked UploadedFile.file_path (authoritative FileField location).
      2. media/submissions/<category_folder>/<stored_filename> (final location, if ever moved).
      3. media/uploads/drafts/<stored_filename> (files are currently never moved after submit).

    Args:
        file_metadata: FileMetadata instance.

    Returns:
        str absolute path, or None.
    """
    from apps.submissions.models import UploadedFile

    # 1. Authoritative: the UploadedFile FileField knows exactly where the file lives.
    uf = UploadedFile.objects.filter(
        application_id=file_metadata.application_id,
        stored_filename=file_metadata.stored_filename,
        is_deleted=False,
    ).first()
    if uf and uf.file_path:
        try:
            uf_path = uf.file_path.path
            if os.path.exists(uf_path):
                return uf_path
        except (ValueError, NotImplementedError):
            pass  # storage without a local filesystem path

    # 2. Final location under submissions/<folder>/
    category_folder = FILE_CATEGORY_FOLDERS.get(file_metadata.file_type, 'submissions')
    final_path = os.path.join(
        settings.MEDIA_ROOT, 'submissions', category_folder, file_metadata.stored_filename
    )
    if os.path.exists(final_path):
        return final_path

    # 3. Drafts location (default, files are not moved after submission)
    drafts_path = os.path.join(
        settings.MEDIA_ROOT, 'uploads', 'drafts', file_metadata.stored_filename
    )
    if os.path.exists(drafts_path):
        return drafts_path

    return None


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

        # Z3 (2026-07-24): Broj lične karte / ID broj no longer collected for fizička lica.

        # Story 5.1: Validate registracioni_broj for pravno lice (replaces maticni_broj validation)
        if applicant_data.get('entity_type') == EntityType.PRAVNO:
            validate_registracioni_broj(applicant_data.get('maticni_broj'))  # Field name kept for backward compatibility

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
            # Z3: jmbg (Broj lične karte / ID broj) no longer collected; column stays nullable.
            maticni_broj=applicant_data.get('maticni_broj')
        )

        # Step 4: Create ProjectData record (COA only)
        # Story 5.2: Added datum_startovanja and datum_zavrsetka
        if application_type == ApplicationType.COA and project_data:
            # Story 5.2: Parse date strings to date objects (YYYY-MM-DD format from HTML5 date input)
            datum_startovanja = None
            datum_zavrsetka = None
            if project_data.get('datum_startovanja'):
                from datetime import datetime
                datum_startovanja = datetime.strptime(project_data['datum_startovanja'], '%Y-%m-%d').date()
            if project_data.get('datum_zavrsetka'):
                from datetime import datetime
                datum_zavrsetka = datetime.strptime(project_data['datum_zavrsetka'], '%Y-%m-%d').date()

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
                datum_startovanja=datum_startovanja,  # Story 5.2
                datum_zavrsetka=datum_zavrsetka,  # Story 5.2
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

    except ValidationError as e:
        # Return validation errors to the user with specific messages
        logger.warning(f"Submission validation error: {str(e)}")
        messages = e.messages if hasattr(e, 'messages') else [str(e)]
        return {
            'success': False,
            'error': ' '.join(messages)
        }

    except Exception as e:
        # Log failure with full traceback
        logger.error(f"Submission FAILURE: {str(e)}", exc_info=True)

        # Return user-friendly error message (no stack trace)
        error_msg = 'Greška pri čuvanju prijave. Molimo pokušajte ponovo.'
        if settings.DEBUG:
            error_msg = f'DEBUG: {str(e)}'
        return {
            'success': False,
            'error': error_msg
        }


class PDFGenerationService:
    """
    Service for generating PDF confirmations for submissions.

    Uses ReportLab library to create professional-looking PDF documents
    with submission details.
    """

    def generate_confirmation_pdf(self, application):
        """
        Generate PDF confirmation for application submission.

        Args:
            application: Application model instance

        Returns:
            BytesIO buffer containing PDF data

        Note:
            Uses Arial Unicode MS font (if available) or FreeSans to support
            Serbian characters (č, ć, š, đ, ž). Falls back to Helvetica if
            Unicode fonts are not available.
        """
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib import colors
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from io import BytesIO
        import os

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )

        # ENCODING FIX: Register font that supports Serbian characters
        # Try to use system fonts or bundled fonts
        font_name = 'Helvetica'  # Default fallback
        font_name_bold = 'Helvetica-Bold'

        # Try to register FreeSans (supports Serbian Latin)
        try:
            # Check if FreeSans is available in system fonts
            # Windows: C:\Windows\Fonts\FreeSans.ttf
            # Linux: /usr/share/fonts/truetype/freefont/FreeSans.ttf
            # macOS: /Library/Fonts/FreeSans.ttf
            freesans_paths = [
                '/usr/share/fonts/truetype/freefont/FreeSans.ttf',  # Linux
                'C:\\Windows\\Fonts\\arial.ttf',  # Windows Arial
                '/System/Library/Fonts/Supplemental/Arial.ttf',  # macOS Arial
            ]

            for font_path in freesans_paths:
                if os.path.exists(font_path):
                    pdfmetrics.registerFont(TTFont('CustomFont', font_path))
                    font_name = 'CustomFont'
                    font_name_bold = 'CustomFont'  # Use same font for bold (TTF doesn't have separate bold)
                    logger.info(f"Registered Unicode font from: {font_path}")
                    break
        except Exception as e:
            logger.warning(f"Failed to register Unicode font: {str(e)}. Using Helvetica fallback.")
            # Continue with Helvetica (will display Latin characters correctly)

        # Container for PDF elements
        elements = []

        # Styles
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            fontName=font_name_bold,
            textColor=colors.HexColor('#0EA5E9'),
            spaceAfter=30,
            alignment=1  # Center
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            fontName=font_name_bold,
            textColor=colors.HexColor('#2C3E50'),
            spaceAfter=12
        )

        ref_style = ParagraphStyle(
            'RefNumber',
            parent=styles['Heading1'],
            fontSize=32,
            fontName=font_name_bold,
            textColor=colors.HexColor('#0EA5E9'),
            alignment=1,
            spaceAfter=20
        )

        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=11,
            fontName=font_name,
            leading=14
        )

        # Title - ENCODING: Use ASCII-safe version to avoid font issues
        elements.append(Paragraph("POTVRDA O PRIJEMU PRIJAVE", title_style))
        elements.append(Spacer(1, 0.5*cm))

        # Reference Number (PROMINENT)
        elements.append(Paragraph(application.reference_number, ref_style))
        elements.append(Spacer(1, 1*cm))

        # Submission Info
        elements.append(Paragraph("Informacije o podnosenju", heading_style))

        submission_data = [
            ['Datum podnosenja:', application.submitted_at.strftime('%d.%m.%Y %H:%M')],
            ['Tip prijave:', 'Projekat (COA)' if application.application_type == 'COA' else 'Inicijativa (COB)'],
            ['Status:', 'Primljeno'],
        ]

        submission_table = Table(submission_data, colWidths=[5*cm, 10*cm])
        submission_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), font_name, 11),
            ('FONT', (0, 0), (0, -1), font_name_bold, 11),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))

        elements.append(submission_table)
        elements.append(Spacer(1, 0.7*cm))

        # Applicant Info
        applicant = application.applicant
        elements.append(Paragraph("Podaci o podnosiocu", heading_style))

        if applicant.entity_type == 'fizicko':
            applicant_data = [
                ['Tip:', 'Fizicko lice'],
                ['Ime i prezime:', f"{applicant.first_name} {applicant.last_name}"],
                ['Adresa:', applicant.address or 'N/A'],
                ['Email:', applicant.email or 'N/A'],
                ['Telefon:', applicant.phone or 'N/A'],
            ]
            # Z3: Broj lične karte / ID broj no longer shown on the confirmation PDF.
        else:  # pravno
            applicant_data = [
                ['Tip:', 'Pravno lice'],
                ['Naziv organizacije:', applicant.organization_name or 'N/A'],
                ['Adresa:', applicant.address or 'N/A'],
                ['Email:', applicant.email or 'N/A'],
                ['Telefon:', applicant.phone or 'N/A'],
            ]
            if applicant.maticni_broj:
                applicant_data.append(['Maticni broj:', applicant.maticni_broj])

        applicant_table = Table(applicant_data, colWidths=[5*cm, 10*cm])
        applicant_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), font_name, 11),
            ('FONT', (0, 0), (0, -1), font_name_bold, 11),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))

        elements.append(applicant_table)
        elements.append(Spacer(1, 0.7*cm))

        # Project/Initiative Info
        if application.application_type == 'COA':
            project_data = application.project_data
            elements.append(Paragraph("Podaci o projektu", heading_style))

            project_info = [
                ['Naslov:', project_data.title or 'N/A'],
                ['Totalni budzet:', f"{project_data.total_budget} EUR" if project_data.total_budget else 'N/A'],
            ]

            project_table = Table(project_info, colWidths=[5*cm, 10*cm])
            project_table.setStyle(TableStyle([
                ('FONT', (0, 0), (-1, -1), font_name, 11),
                ('FONT', (0, 0), (0, -1), font_name_bold, 11),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))

            elements.append(project_table)

        elements.append(Spacer(1, 1*cm))

        # Footer - Use ASCII-safe characters
        footer_text = """
        <para align=center>
        <b>Hvala na podnosenju prijave!</b><br/>
        <br/>
        Bicete obavesteni putem emaila o daljem toku procesa.<br/>
        Ako imate pitanja, kontaktirajte nas na info@domovik.org<br/>
        <br/>
        <i>DOMOVIK</i>
        </para>
        """

        elements.append(Paragraph(footer_text, normal_style))

        # Build PDF
        try:
            doc.build(elements)
        except Exception as e:
            logger.error(f"PDF generation failed: {str(e)}", exc_info=True)
            raise

        buffer.seek(0)
        return buffer


def log_admin_action(user, action, application=None, old_value=None, new_value=None, request=None):
    """
    Log an admin action to the AdminLog table.
    Story 4.6: Admin Activity Logging.

    Args:
        user: Admin user performing the action (User instance)
        action: Action type constant (e.g., ADMIN_ACTION_VIEWED)
        application: Application being acted upon (Application instance, optional)
        old_value: Previous value for changes (str, optional)
        new_value: New value for changes (str, optional)
        request: HTTP request object to extract IP and user agent (HttpRequest, optional)

    Returns:
        AdminLog: Created AdminLog instance

    Example:
        >>> from apps.submissions.constants import ADMIN_ACTION_STATUS_CHANGE
        >>> log_admin_action(
        ...     user=request.user,
        ...     action=ADMIN_ACTION_STATUS_CHANGE,
        ...     application=application,
        ...     old_value='submitted',
        ...     new_value='approved',
        ...     request=request
        ... )
        <AdminLog: 2025-12-30 12:00:00 - admin - changed_status - COA-2025-001>
    """
    from apps.submissions.models import AdminLog

    # Extract IP address from request
    ip_address = None
    if request:
        # Check for X-Forwarded-For header (proxy support)
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # X-Forwarded-For can contain multiple IPs (client, proxy1, proxy2...)
            # First IP is the original client
            ip_address = x_forwarded_for.split(',')[0].strip()
        else:
            # Fall back to REMOTE_ADDR (direct connection)
            ip_address = request.META.get('REMOTE_ADDR')

    # Extract user agent from request
    user_agent = None
    if request:
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        # Truncate to 500 chars to prevent excessively long strings
        if len(user_agent) > 500:
            user_agent = user_agent[:500]

    # Create log entry
    try:
        log_entry = AdminLog.objects.create(
            user=user,
            action=action,
            application=application,
            old_value=old_value,
            new_value=new_value,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Also log to Python logger for debugging
        if application:
            logger.info(
                f"Admin action logged: {action} by {user.username} on {application.reference_number}"
            )
        else:
            logger.info(
                f"Admin action logged: {action} by {user.username}"
            )

        return log_entry

    except Exception as e:
        # Log error but don't fail the request
        logger.error(f"Failed to log admin action: {str(e)}", exc_info=True)
        # Re-raise exception so caller knows logging failed
        raise


# Export list for module
__all__ = [
    'ReferenceNumberService',
    'process_submission',
    'PDFGenerationService',
    'log_admin_action',
]
