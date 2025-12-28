# -*- coding: utf-8 -*-
"""
Views for COA/COB application submission.
Story 1.3: Created placeholder views
Story 2.2: Add COAFormSectionI form handling
Story 2.8: File upload/delete API endpoints
Story 2.11: Submission processing endpoint with rate limiting and duplicate prevention
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
from apps.submissions.models import UploadedFile, Application, Applicant
from apps.submissions.validators import generate_unique_filename
from apps.submissions.services import process_submission

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


class InitiativeApplicationView(TemplateView):
    """
    Placeholder view for COB (Initiative) application form.
    Full implementation in Epic 3 (Stories 3.1-3.6).
    """
    template_name = 'submissions/cob_form.html'


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
