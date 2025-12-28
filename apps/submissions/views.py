# -*- coding: utf-8 -*-
"""
Views for COA/COB application submission.
Story 1.3: Created placeholder views
Story 2.2: Add COAFormSectionI form handling
Story 2.8: File upload/delete API endpoints
Story 2.11: Submission processing endpoint with rate limiting and duplicate prevention
Story 2.15: Draft registration and expiration check API endpoints
"""
import logging
import json
from datetime import timedelta
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils.decorators import method_decorator
from django.utils import timezone
from django_ratelimit.decorators import ratelimit
from apps.submissions.forms import COAFormSectionI, FileUploadForm
from apps.submissions.models import UploadedFile, Application, Applicant, DraftMetadata
from apps.submissions.validators import generate_unique_filename
from apps.submissions.services import process_submission, PDFGenerationService
from apps.submissions.tasks import send_confirmation_email
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, Http404

# File upload logger
logger = logging.getLogger('file_uploads')
submission_logger = logging.getLogger('domovik.submissions')


@method_decorator(ensure_csrf_cookie, name='dispatch')
class ProjectApplicationView(TemplateView):
    """
    COA (Projekat) application form view.

    Story 1.3: Basic template rendering
    Story 2.2: Add Section I form handling (GET request - display form)
    Story 2.11: Add POST request handling (form submission)

    CSRF Cookie: ensure_csrf_cookie decorator ensures CSRF cookie is set
    for JavaScript file upload functionality.
    """
    template_name = 'submissions/coa_form.html'

    def get_context_data(self, **kwargs):
        """Add COAFormSectionI form to context"""
        context = super().get_context_data(**kwargs)
        context['form'] = COAFormSectionI()
        context['current_section'] = 1  # Section I
        return context


@ensure_csrf_cookie
@require_http_methods(['GET'])
def cob_form(request):
    """
    COB (Inicijativa) form view - Simplified application flow.
    Story 3.1: COB Routing & Form Initialization

    Differences from COA:
    - NO JMBG field (fizičko lice)
    - NO matični broj field (pravno lice)
    - Simpler Section II (no budget)
    - Only 2 file uploads (vs COA's 3+)

    Reuses:
    - Draft system (DraftManager with application_type='COB')
    - Validation infrastructure (email, phone, character counter)
    - File upload system (same backend)
    - Progress stepper (3 sections)

    Security:
    - CSRF cookie ensured for file upload functionality
    - HTTP GET method only (no form processing)
    """
    context = {
        'application_type': 'COB',  # Critical for draft-manager.js
        'form_title': 'Prijava za Inicijativu (COB)',
        'sections': [
            {'number': 1, 'title': 'Opšti podaci'},
            {'number': 2, 'title': 'Podaci o inicijativi'},
            {'number': 3, 'title': 'Dokumentacija i saglasnost'},
        ],
        'entity_types': [
            {'value': 'fizicko', 'label': 'Fizičko lice'},
            {'value': 'pravno', 'label': 'Pravno lice'},
        ],
        # Character limits (from epics.md - Story 3.3)
        'char_limits': {
            'naslov': 150,
            'kratak_opis': 500,
            'problem': 1500,
            'cilj': 1500,
            'planirani_koraci': 1500,
            'ocekivani_uticaj': 1500,
        },
        # File upload requirements (Story 3.4)
        'required_files': [
            {'id': 'opis_inicijative', 'label': 'Opis inicijative (PDF/DOC)', 'accept': '.pdf,.doc,.docx', 'required': True},
            {'id': 'pismo_namere', 'label': 'Pismo namere (PDF/DOC)', 'accept': '.pdf,.doc,.docx', 'required': True},
        ],
        # Privacy policy links (same as COA)
        'privacy_policy_url': '/politika-privatnosti/',
        'terms_of_use_url': '/uslovi-koristenja/',
    }

    return render(request, 'submissions/cob_form.html', context)


@csrf_protect
@require_http_methods(['POST'])
def upload_file(request):
    """
    File upload API endpoint.
    Story 2.8: Handle file upload with comprehensive validation

    Validates:
    - File extension (PDF, DOC, DOCX, XLS, XLSX only)
    - File size (10MB max)
    - MIME type (prevents extension spoofing)

    Security Features:
    - CSRF protection
    - Extension whitelist
    - Size limit enforcement
    - MIME type validation
    - Unique filename generation
    - Session-based ownership

    Returns:
        JsonResponse: Success with file metadata or error details
    """
    try:
        # Ensure session exists
        if not request.session.session_key:
            request.session.create()

        # Validate form
        form = FileUploadForm(request.POST, request.FILES)

        if form.is_valid():
            uploaded_file = request.FILES['file']
            category = form.cleaned_data['category']

            # Generate unique filename
            unique_name = generate_unique_filename(uploaded_file.name)

            # Determine file type (extension)
            file_type = uploaded_file.name.split('.')[-1].lower() if '.' in uploaded_file.name else ''

            # Save to media/uploads/drafts/
            file_path = f'uploads/drafts/{unique_name}'
            saved_path = default_storage.save(file_path, ContentFile(uploaded_file.read()))

            # Create database record
            file_record = UploadedFile.objects.create(
                original_filename=uploaded_file.name,
                stored_filename=unique_name,
                file_path=saved_path,
                file_size=uploaded_file.size,
                file_type=file_type,
                mime_type=uploaded_file.content_type or 'application/octet-stream',
                category=category,
                uploaded_by_session=request.session.session_key
            )

            # Log success
            logger.info(
                f"File uploaded successfully: {uploaded_file.name}, "
                f"size: {uploaded_file.size}, "
                f"category: {category}, "
                f"session: {request.session.session_key}"
            )

            return JsonResponse({
                'success': True,
                'file_id': file_record.id,
                'filename': file_record.original_filename,
                'size': file_record.file_size,
                'file_type': file_record.file_type,
                'category': file_record.category,
                'message': 'Fajl je uspešno upload-ovan.'
            })
        else:
            # Log validation failure
            logger.error(
                f"Upload validation failed: {form.errors.as_json()}, "
                f"session: {request.session.session_key}"
            )

            return JsonResponse({
                'success': False,
                'errors': form.errors.get_json_data()
            }, status=400)

    except Exception as e:
        # Log exception
        logger.error(
            f"Upload exception: {str(e)}, "
            f"session: {request.session.session_key if request.session.session_key else 'NO_SESSION'}"
        )

        return JsonResponse({
            'success': False,
            'error': 'Došlo je do greške tokom upload-a. Molimo pokušajte ponovo.'
        }, status=500)


@csrf_protect
@require_http_methods(['POST', 'DELETE'])
def delete_file(request, file_id):
    """
    File deletion API endpoint.
    Story 2.8: Handle file deletion with ownership validation

    Security Features:
    - CSRF protection
    - Session-based ownership validation
    - Prevents deletion of other users' files
    - Soft delete with is_deleted flag

    Args:
        request: Django request object
        file_id: ID of file to delete

    Returns:
        JsonResponse: Success or error message
    """
    try:
        # Ensure session exists
        if not request.session.session_key:
            return JsonResponse({
                'success': False,
                'error': 'Sesija nije pronađena. Molimo osvežite stranicu.'
            }, status=403)

        # Get file record
        try:
            file_record = UploadedFile.objects.get(id=file_id, is_deleted=False)
        except UploadedFile.DoesNotExist:
            logger.warning(
                f"Delete attempt for non-existent file: {file_id}, "
                f"session: {request.session.session_key}"
            )
            return JsonResponse({
                'success': False,
                'error': 'Fajl nije pronađen.'
            }, status=404)

        # Verify session ownership
        if file_record.uploaded_by_session != request.session.session_key:
            logger.warning(
                f"Unauthorized delete attempt: file_id={file_id}, "
                f"owner_session={file_record.uploaded_by_session}, "
                f"requester_session={request.session.session_key}"
            )
            return JsonResponse({
                'success': False,
                'error': 'Nemate dozvolu da obrišete ovaj fajl.'
            }, status=403)

        # Delete physical file
        if file_record.file_path and default_storage.exists(file_record.file_path.name):
            default_storage.delete(file_record.file_path.name)

        # Soft delete - mark as deleted
        file_record.is_deleted = True
        file_record.save()

        # Log deletion
        logger.info(
            f"File deleted: file_id={file_id}, "
            f"filename={file_record.original_filename}, "
            f"session={request.session.session_key}"
        )

        return JsonResponse({
            'success': True,
            'message': 'Fajl je uspešno obrisan.'
        })

    except Exception as e:
        # Log exception
        logger.error(
            f"Delete exception: {str(e)}, "
            f"file_id: {file_id}, "
            f"session: {request.session.session_key if request.session.session_key else 'NO_SESSION'}"
        )

        return JsonResponse({
            'success': False,
            'error': 'Došlo je do greške tokom brisanja. Molimo pokušajte ponovo.'
        }, status=500)


@csrf_protect
@require_http_methods(['POST'])
@ratelimit(key='ip', rate='10/h', method='POST', block=True)
def submit_application(request):
    """
    Complete application submission endpoint.
    Story 2.11: Handle COA/COB submission with reference number generation

    Processes:
    - Form data validation (applicant + project)
    - File metadata collection from session
    - Atomic database transaction (reference number, applicant, project, files)
    - Draft cleanup on success
    - Error handling with rollback

    Security Features:
    - CSRF protection
    - Rate limiting (10 submissions per hour per IP)
    - Duplicate submission prevention (same email + title in last 5 minutes)
    - JSON request body
    - Session-based file ownership validation
    - Atomic transactions (no partial submissions)

    Returns:
        JsonResponse: Success with reference number or error details
    """
    try:
        # Parse JSON request body
        try:
            submission_data = json.loads(request.body.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error(f"Invalid JSON in submission: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'Neispravni podaci. Molimo pokušajte ponovo.'
            }, status=400)

        # Validate required fields
        if not submission_data.get('applicant'):
            return JsonResponse({
                'success': False,
                'error': 'Podaci o podnosiocu nisu pronađeni.'
            }, status=400)

        # Get application type (COA by default)
        application_type = submission_data.get('application_type', 'COA')

        # Validate project data for COA
        if application_type == 'COA' and not submission_data.get('project'):
            return JsonResponse({
                'success': False,
                'error': 'Podaci o projektu nisu pronađeni.'
            }, status=400)

        # Duplicate submission prevention: Check for same email + title in last 5 minutes
        applicant_email = submission_data.get('applicant', {}).get('email')
        project_title = submission_data.get('project', {}).get('title') if application_type == 'COA' else None

        if applicant_email and project_title:
            five_minutes_ago = timezone.now() - timedelta(minutes=5)
            recent_submissions = Application.objects.filter(
                applicant__email=applicant_email,
                project_data__title=project_title,
                submitted_at__gte=five_minutes_ago
            ).exists()

            if recent_submissions:
                submission_logger.warning(
                    f"Duplicate submission blocked: email={applicant_email}, "
                    f"title={project_title[:50]}, ip={request.META.get('REMOTE_ADDR')}"
                )
                return JsonResponse({
                    'success': False,
                    'error': 'Već ste poslali istu prijavu u poslednjih 5 minuta. Molimo sačekajte pre nego što pokušate ponovo.'
                }, status=429)

        # Get uploaded files from session
        session_key = request.session.session_key
        if not session_key:
            logger.warning("Submission attempt without session")
            return JsonResponse({
                'success': False,
                'error': 'Sesija je istekla. Molimo osvežite stranicu i pokušajte ponovo.'
            }, status=403)

        # Fetch uploaded files for this session
        uploaded_files = UploadedFile.objects.filter(
            uploaded_by_session=session_key,
            is_deleted=False,
            application__isnull=True  # Only draft files
        )

        # Build file metadata list
        files_metadata = []
        for file_obj in uploaded_files:
            files_metadata.append({
                'file_type': file_obj.category,
                'original_filename': file_obj.original_filename,
                'stored_filename': file_obj.stored_filename,
                'file_size': file_obj.file_size
            })

        # Add files to submission data
        submission_data['files'] = files_metadata

        # Process submission using service (atomic transaction)
        result = process_submission(submission_data)

        if result['success']:
            # Link uploaded files to application
            # Note: We'll need to fetch the application to link files
            application_obj = Application.objects.get(
                reference_number=result['reference_number']
            )
            uploaded_files.update(application=application_obj)

            # Trigger async email task (Story 2.14)
            # SECURITY: Don't log email addresses (GDPR compliance)
            submission_logger.info(
                f"Triggering email confirmation task for {result['reference_number']}"
            )
            send_confirmation_email.delay(application_obj.id)

            logger.info(
                f"Submission completed successfully: {result['reference_number']}, "
                f"session: {session_key}"
            )

            return JsonResponse({
                'success': True,
                'reference_number': result['reference_number'],
                'message': f"Prijava je uspešno podnesena. Vaš referentni broj: {result['reference_number']}"
            })
        else:
            # Return error from process_submission
            logger.error(f"Submission failed: {result.get('error')}")
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Greška pri čuvanju prijave.')
            }, status=500)

    except Exception as e:
        # Log unexpected exception
        logger.error(f"Unexpected submission error: {str(e)}", exc_info=True)

        return JsonResponse({
            'success': False,
            'error': 'Došlo je do neočekivane greške. Molimo pokušajte ponovo ili kontaktirajte podršku.'
        }, status=500)


@require_http_methods(['GET'])
def success_screen(request, application_type, reference_number):
    """
    Display success screen after successful submission.
    Story 2.13: Success Screen with Reference Number

    Args:
        application_type: 'COA' or 'COB'
        reference_number: Full reference number (e.g., 'COA-2025-003')

    Returns:
        Rendered success screen with reference number

    Security:
        - Reference number validated against regex pattern (SQL injection prevention)
        - HTTP method restricted to GET only
        - Application existence verified before rendering
    """
    import re

    # SECURITY: Validate reference number format with regex (prevent SQL injection)
    # Format: COA-YYYY-NNN or COB-YYYY-NNN
    # Example: COA-2025-003, COB-2025-123
    ref_pattern = r'^(COA|COB)-\d{4}-\d{3}$'
    if not re.match(ref_pattern, reference_number):
        logger.warning(f"Invalid reference number format: {reference_number}")
        raise Http404("Nevažeći format referentnog broja")

    # SECURITY: Validate application_type is exactly 'COA' or 'COB'
    if application_type not in ['COA', 'COB']:
        logger.warning(f"Invalid application type: {application_type}")
        raise Http404("Nevažeći tip prijave")

    # Additional validation: reference_number must start with application_type
    if not reference_number.startswith(f"{application_type}-"):
        logger.warning(f"Reference number {reference_number} doesn't match type {application_type}")
        raise Http404("Referentni broj ne odgovara tipu prijave")

    # Get application from database (verify it exists)
    # get_object_or_404 prevents DoesNotExist exception
    application = get_object_or_404(
        Application,
        reference_number=reference_number,
        application_type=application_type
    )

    # Get applicant email for display
    applicant_email = application.applicant.email if application.applicant else "N/A"

    context = {
        'reference_number': reference_number,
        'application_type': application_type,
        'applicant_email': applicant_email,
        'submission_date': application.submitted_at,
        'application': application,
    }

    return render(request, 'submissions/success.html', context)


@require_http_methods(['GET'])
def download_pdf_confirmation(request, reference_number):
    """
    Generate and download PDF confirmation for submission.
    Story 2.13: PDF Download

    Args:
        reference_number: Full reference number (e.g., 'COA-2025-003')

    Returns:
        PDF file as HTTP response

    Security:
        - Reference number validated against regex pattern (SQL injection prevention)
        - Filename sanitized to prevent path traversal attacks
        - HTTP method restricted to GET only
    """
    import re

    # SECURITY: Validate reference number format with regex (prevent SQL injection)
    ref_pattern = r'^(COA|COB)-\d{4}-\d{3}$'
    if not re.match(ref_pattern, reference_number):
        logger.warning(f"Invalid reference number in PDF download: {reference_number}")
        raise Http404("Nevažeći format referentnog broja")

    # Get application from database
    application = get_object_or_404(Application, reference_number=reference_number)

    # Generate PDF using PDFGenerationService
    pdf_service = PDFGenerationService()
    pdf_buffer = pdf_service.generate_confirmation_pdf(application)

    # SECURITY: Sanitize filename to prevent path traversal
    # Remove any path separators and special characters
    safe_filename = reference_number.replace('/', '_').replace('\\', '_').replace('..', '_')
    filename = f"Potvrda_{safe_filename}.pdf"

    # Create HTTP response with PDF
    response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    return response


@csrf_protect
@require_http_methods(['POST'])
def resend_email(request, reference_number):
    """
    Resend email confirmation to applicant.
    Story 2.13: Email Resend (stub implementation)

    Args:
        reference_number: Full reference number (e.g., 'COA-2025-003')

    Returns:
        JSON response with success/error message

    Security:
        - Reference number validated against regex pattern (SQL injection prevention)
        - CSRF protection enabled
        - HTTP method restricted to POST only
    """
    import re

    # SECURITY: Validate reference number format with regex (prevent SQL injection)
    ref_pattern = r'^(COA|COB)-\d{4}-\d{3}$'
    if not re.match(ref_pattern, reference_number):
        logger.warning(f"Invalid reference number in email resend: {reference_number}")
        return JsonResponse({
            'success': False,
            'message': 'Nevažeći format referentnog broja.'
        }, status=400)

    # Get application from database
    try:
        application = Application.objects.get(reference_number=reference_number)
    except Application.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': f"Prijava sa referentnim brojem {reference_number} nije pronađena."
        }, status=404)

    # Story 2.14: Trigger Celery email task
    logger.info(f"Resending email confirmation for {reference_number}")
    send_confirmation_email.delay(application.id)

    return JsonResponse({
        'success': True,
        'message': f"Email potvrda je poslata na {application.applicant.email}."
    })


@csrf_protect
@require_http_methods(['POST'])
def register_draft(request):
    """
    Register client-side draft creation on server for GDPR tracking.
    Story 2.15: Draft Auto-Deletion Background Task

    Request JSON:
        {
            "draft_id": "uuid-string",
            "application_type": "COA" or "COB"
        }

    Privacy: NO form data accepted or stored.

    Returns:
        {
            "success": true,
            "message": "Draft registered for 7-day retention tracking",
            "expires_at": "ISO datetime string"
        }
    """
    try:
        data = json.loads(request.body)
        draft_id = data.get('draft_id')
        application_type = data.get('application_type')

        # Validation
        if not draft_id or not application_type:
            return JsonResponse({
                'success': False,
                'message': 'draft_id and application_type required'
            }, status=400)

        if application_type not in ['COA', 'COB']:
            return JsonResponse({
                'success': False,
                'message': 'application_type must be COA or COB'
            }, status=400)

        # ISSUE 1 FIX: Validate UUID format before database operation
        try:
            import uuid as uuid_module
            uuid_module.UUID(str(draft_id))
        except (ValueError, AttributeError):
            logger.warning(f"Invalid UUID format in draft registration: {draft_id}")
            return JsonResponse({
                'success': False,
                'message': 'Invalid draft_id format - must be valid UUID'
            }, status=400)

        # ISSUE 8 PARTIAL FIX: Register or update draft metadata
        # NOTE: Race condition edge case still exists - if Celery deletes draft while user editing,
        # next auto-save will recreate it with fresh created_at timestamp (clock reset).
        # This is acceptable behavior: User gets extra 7 days, which is better UX than losing work.
        # Alternative (rejected): Track "deleted_draft_ids" table - adds complexity for minimal gain.
        draft, created = DraftMetadata.objects.update_or_create(
            draft_id=draft_id,
            defaults={'application_type': application_type}
        )

        action = "registered" if created else "updated"
        logger.info(f"Draft {draft_id} ({application_type}) {action} for GDPR tracking")

        return JsonResponse({
            'success': True,
            'message': f'Draft {action} for 7-day retention tracking',
            'expires_at': (draft.created_at + timedelta(days=7)).isoformat()
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON in request body'
        }, status=400)

    except Exception as e:
        logger.error(f"Draft registration failed: {e}")
        return JsonResponse({
            'success': False,
            'message': 'Internal server error'
        }, status=500)


@csrf_protect
@require_http_methods(['POST'])
def check_draft_expiration(request, draft_id):
    """
    Check if draft has expired server-side (>7 days old or deleted).
    Story 2.15: Draft Auto-Deletion Background Task

    Called by client on page load to sync localStorage with server.

    Returns:
        {
            "exists": true/false,
            "expired": true/false (only if exists),
            "created_at": "ISO datetime string" (only if exists)
        }
    """
    try:
        draft = DraftMetadata.objects.get(draft_id=draft_id)

        return JsonResponse({
            'exists': True,
            'expired': draft.is_expired(),
            'created_at': draft.created_at.isoformat()
        })

    except DraftMetadata.DoesNotExist:
        # Draft not found on server - client should delete localStorage
        return JsonResponse({
            'exists': False,
            'expired': True  # Treat missing as expired
        })
