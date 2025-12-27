# -*- coding: utf-8 -*-
"""
Views for COA/COB application submission.
Story 1.3: Created placeholder views
Story 2.2: Add COAFormSectionI form handling
Story 2.8: File upload/delete API endpoints
"""
import logging
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils.decorators import method_decorator
from apps.submissions.forms import COAFormSectionI, FileUploadForm
from apps.submissions.models import UploadedFile
from apps.submissions.validators import generate_unique_filename

# File upload logger
logger = logging.getLogger('file_uploads')


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
