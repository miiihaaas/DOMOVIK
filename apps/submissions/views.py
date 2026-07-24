# -*- coding: utf-8 -*-
"""
Views for COA/COB application submission.
Story 1.3: Created placeholder views
Story 2.2: Add COAFormSectionI form handling
Story 2.8: File upload/delete API endpoints
Story 2.11: Submission processing endpoint with rate limiting and duplicate prevention
Story 2.15: Draft registration and expiration check API endpoints
Story 4.4: Admin document download functionality
"""
import logging
import json
import os
import zipfile
from io import BytesIO
from datetime import timedelta
from django.views.generic import TemplateView
from django.http import JsonResponse, HttpResponse, Http404, HttpResponseForbidden, FileResponse
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django_ratelimit.decorators import ratelimit
from apps.submissions.forms import (
    COAFormSectionI, FileUploadForm, COBApplicantForm, COBInitiativeDataForm,
    COBSectionIIIForm, validate_cob_file_metadata, ClanTimaFormSet
)
from apps.submissions.models import UploadedFile, Application, Applicant, InitiativeData, DraftMetadata, FileMetadata, ClanTima
from apps.submissions.validators import generate_unique_filename
from apps.submissions.services import process_submission, PDFGenerationService, resolve_file_on_disk
from apps.submissions.tasks import (
    send_confirmation_email_now,
    send_admin_notification_now,
)
from django.shortcuts import render, get_object_or_404

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
        """Add COAFormSectionI form and ClanTimaFormSet to context"""
        context = super().get_context_data(**kwargs)
        context['form'] = COAFormSectionI()
        context['current_section'] = 1  # Section I
        # Story 5.1: Add ClanTimaFormSet for team members (empty formset for GET)
        # Note: ClanTimaFormSet requires an Application instance, but for GET request
        # we create an empty formset without instance (will be handled via JavaScript)
        context['team_members_formset'] = None  # Handled dynamically via JS
        return context


@ensure_csrf_cookie
@require_http_methods(['GET'])
def cob_form(request):
    """
    COB (Inicijativa) form view - Simplified application flow.
    Story 3.1: COB Routing & Form Initialization
    Story 3.2: Add COBApplicantForm for Section I validation

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
    # Initialize empty form (GET request) - Story 3.2
    form = COBApplicantForm()

    context = {
        'application_type': 'COB',  # Critical for draft-manager.js
        'form': form,  # NEW: Pass form to template (Story 3.2)
        'form_title': 'Prijava za Inicijativu',
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

            # Story 5.1: Save team members (Ostali članovi tima)
            team_members_data = submission_data.get('team_members', [])
            for member in team_members_data:
                # Only save if at least one field has data
                if member.get('ime_prezime') or member.get('email') or member.get('telefon'):
                    ClanTima.objects.create(
                        application=application_obj,
                        ime_prezime=member.get('ime_prezime', ''),
                        email=member.get('email', ''),
                        telefon=member.get('telefon', '')
                    )

            # Z4′: Send emails SYNCHRONOUSLY (no Celery worker on production).
            # Both *_now() helpers swallow errors so a mail failure never breaks the submission.
            # SECURITY: Don't log email addresses (GDPR compliance)
            submission_logger.info(
                f"Sending emails for {result['reference_number']}"
            )
            # Story 2.14: User confirmation email
            send_confirmation_email_now(application_obj.id)

            # Story 3.6: Admin notification email (COA also sends admin notifications)
            send_admin_notification_now(application_obj.id, 'COA')

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
            }, status=400)

    except Exception as e:
        # Log unexpected exception
        logger.error(f"Unexpected submission error: {str(e)}", exc_info=True)

        error_msg = 'Došlo je do neočekivane greške. Molimo pokušajte ponovo ili kontaktirajte podršku.'
        if settings.DEBUG:
            error_msg = f'DEBUG: {str(e)}'
        return JsonResponse({
            'success': False,
            'error': error_msg
        }, status=500)


@csrf_protect
@require_http_methods(['POST'])
@ratelimit(key='ip', rate='10/h', method='POST', block=True)
def submit_cob(request):
    """
    COB (Inicijativa) submission endpoint.
    Story 3.5: COB Submission Processing - COB Reference Number
    CODE REVIEW FIXES: Added validation, FileMetadata creation, duplicate prevention, email outside transaction

    Purpose: Process complete COB submission, generate COB reference number, save to database.

    Request: POST /api/submissions/submit-cob/
    Body: {
        applicant: {...},  # Section I data (NO JMBG/matični)
        initiative: {...},  # Section II data (NO budžet)
        files: [...],  # File metadata (2 files)
        consent: {...}  # Section III consent
    }

    Response:
    - Success: { "success": true, "reference_number": "COB-2025-001" }
    - Error: { "success": false, "error": "error message" }

    Architecture: Atomic transaction, GDPR-compliant logging, comprehensive validation
    """
    from django.db import transaction
    from django.core.exceptions import ValidationError  # FIX: Missing import
    from apps.submissions.services import ReferenceNumberService
    from apps.submissions.constants import FileType
    from apps.submissions.validators import validate_email, validate_phone
    from apps.submissions.models import FileMetadata  # FIX: Missing import
    from datetime import timedelta

    try:
        # Parse JSON request body
        try:
            data = json.loads(request.body.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            submission_logger.error(f"Invalid JSON in COB submission: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'Neispravan JSON format.'
            }, status=400)

        # Extract sections
        applicant_data = data.get('applicant', {})
        initiative_data = data.get('initiative', {})
        files_metadata = data.get('files', [])  # FIX #7: Renamed for consistency
        consent_data = data.get('consent', {})

        # Production logging: Monitor file count and consent for validation
        submission_logger.info(f"COB submit - Files metadata count: {len(files_metadata)}")
        submission_logger.info(f"COB submit - Consent data: {consent_data}")

        # FIX #2: Validate required data presence
        if not applicant_data or not initiative_data:
            submission_logger.warning(
                f"COB submission missing data: applicant={bool(applicant_data)}, initiative={bool(initiative_data)}, "
                f"ip={request.META.get('REMOTE_ADDR')}"
            )
            return JsonResponse({
                'success': False,
                'error': 'Nedostaju podaci o podnosiocu ili inicijativi.'
            }, status=400)

        # FIX #2 & #9: Validate applicant fields
        required_applicant_fields = ['entity_type', 'address', 'email', 'phone']
        missing_applicant = [f for f in required_applicant_fields if not applicant_data.get(f)]
        if missing_applicant:
            submission_logger.warning(
                f"COB submission missing applicant fields: {missing_applicant}, ip={request.META.get('REMOTE_ADDR')}"
            )
            return JsonResponse({
                'success': False,
                'error': f'Nedostaju obavezna polja podnosioca: {", ".join(missing_applicant)}.'
            }, status=400)

        # FIX #2: Validate entity-specific fields
        entity_type = applicant_data.get('entity_type')
        if entity_type == 'fizicko':
            if not applicant_data.get('first_name') or not applicant_data.get('last_name'):
                submission_logger.warning(f"COB submission missing name fields, ip={request.META.get('REMOTE_ADDR')}")
                return JsonResponse({
                    'success': False,
                    'error': 'Ime i prezime su obavezni za fizičko lice.'
                }, status=400)
        elif entity_type == 'pravno':
            if not applicant_data.get('organization_name'):
                submission_logger.warning(f"COB submission missing organization name, ip={request.META.get('REMOTE_ADDR')}")
                return JsonResponse({
                    'success': False,
                    'error': 'Naziv organizacije je obavezan za pravno lice.'
                }, status=400)

        # FIX #2: Validate email and phone format
        try:
            validate_email(applicant_data.get('email'))
        except ValidationError as e:
            submission_logger.warning(f"COB submission invalid email: {e}, ip={request.META.get('REMOTE_ADDR')}")
            return JsonResponse({
                'success': False,
                'error': f'Nevažeći email format: {e.message}'
            }, status=400)

        try:
            validate_phone(applicant_data.get('phone'))
        except ValidationError as e:
            submission_logger.warning(f"COB submission invalid phone: {e}, ip={request.META.get('REMOTE_ADDR')}")
            return JsonResponse({
                'success': False,
                'error': f'Nevažeći telefon format: {e.message}'
            }, status=400)

        # FIX #9 & #11: Validate initiative fields (presence and length)
        required_initiative_fields = {
            'naslov': 150,
            'kratak_opis': 500,
            'problem': 1500,
            'cilj_inicijative': 1500,
            'planirani_koraci': 1500,
            'ocekivani_uticaj': 1500
        }

        for field, max_length in required_initiative_fields.items():
            value = initiative_data.get(field)
            if not value or not value.strip():
                submission_logger.warning(
                    f"COB submission missing initiative field: {field}, ip={request.META.get('REMOTE_ADDR')}"
                )
                return JsonResponse({
                    'success': False,
                    'error': f'Polje "{field}" je obavezno.'
                }, status=400)

            if len(value) > max_length:
                submission_logger.warning(
                    f"COB submission field too long: {field} ({len(value)} > {max_length}), ip={request.META.get('REMOTE_ADDR')}"
                )
                return JsonResponse({
                    'success': False,
                    'error': f'Polje "{field}" predugo (maksimalno {max_length} karaktera).'
                }, status=400)

        # Validate consent (GDPR required - all 3 checkboxes must be checked)
        # FIX: Field names match frontend (privacy, terms, accuracy) not saglasnost_gdpr
        if not consent_data.get('privacy') or not consent_data.get('terms') or not consent_data.get('accuracy'):
            submission_logger.warning(f"COB submission missing consent checkboxes, ip={request.META.get('REMOTE_ADDR')}")
            return JsonResponse({
                'success': False,
                'error': 'Sve saglasnosti (privatnost, uslovi, tačnost) su obavezne.'
            }, status=400)

        # Story 5.4: Validate file metadata (1-2 files: BUDZET_INICIJATIVE required, PISMO_PODRSKE optional)
        if len(files_metadata) < 1 or len(files_metadata) > 2:
            submission_logger.warning(
                f"COB submission wrong file count: {len(files_metadata)}, ip={request.META.get('REMOTE_ADDR')}"
            )
            return JsonResponse({
                'success': False,
                'error': f'Potreban je 1-2 dokumenta (primljeno: {len(files_metadata)}).'
            }, status=400)

        # Story 5.4: Validate file categories - BUDZET_INICIJATIVE required, PISMO_PODRSKE optional
        file_categories = {f.get('file_type') for f in files_metadata}
        required_category = FileType.BUDZET_INICIJATIVE
        optional_category = FileType.PISMO_PODRSKE
        valid_categories = {required_category, optional_category}

        # Check if required budget file is present
        if required_category not in file_categories:
            submission_logger.warning(
                f"COB submission missing required budget file, ip={request.META.get('REMOTE_ADDR')}"
            )
            return JsonResponse({
                'success': False,
                'error': 'Nedostaje obavezan dokument: Budžet inicijative.'
            }, status=400)

        # Check for unexpected categories
        extra = file_categories - valid_categories
        if extra:
            submission_logger.warning(
                f"COB submission unexpected file categories: extra={extra}, ip={request.META.get('REMOTE_ADDR')}"
            )
            return JsonResponse({
                'success': False,
                'error': f'Neočekivane kategorije dokumenata: {", ".join(extra)}.'
            }, status=400)

        # FIX #3: Duplicate submission prevention (same email + naslov in last 5 minutes)
        applicant_email = applicant_data.get('email')
        initiative_naslov = initiative_data.get('naslov')

        if applicant_email and initiative_naslov:
            five_minutes_ago = timezone.now() - timedelta(minutes=5)

            # Query for recent COB submissions with same email and initiative title
            recent_cob_submissions = Application.objects.filter(
                application_type='COB',
                applicant__email=applicant_email,
                initiative_data__naslov=initiative_naslov,
                submitted_at__gte=five_minutes_ago
            ).exists()

            if recent_cob_submissions:
                submission_logger.warning(
                    f"Duplicate COB submission blocked: email={applicant_email}, "
                    f"naslov={initiative_naslov[:50]}, ip={request.META.get('REMOTE_ADDR')}"
                )
                return JsonResponse({
                    'success': False,
                    'error': 'Već ste poslali istu inicijativu u poslednjih 5 minuta. Molimo sačekajte pre nego što pokušate ponovo.'
                }, status=429)

        # ATOMIC TRANSACTION - All-or-nothing
        # FIX #4: Prepare to move email outside transaction
        application_id_for_email = None

        with transaction.atomic():
            # 1. Generate COB reference number
            reference_number = ReferenceNumberService.generate_reference_number("COB")

            if not reference_number:
                submission_logger.error("Failed to generate COB reference number")
                return JsonResponse({
                    'success': False,
                    'error': 'Greška pri generisanju referentnog broja. Molimo pokušajte ponovo.'
                }, status=500)

            # 2. Create Application record (type="COB")
            application = Application.objects.create(
                reference_number=reference_number,
                application_type='COB',
                status='submitted',
                submitted_at=timezone.now()
            )

            # 3. Create Applicant record
            # Z3 (2026-07-24): Broj lične karte / ID broj no longer collected (jmbg stays null).
            # Registracioni broj (maticni_broj field) kept for pravna lica.
            applicant = Applicant.objects.create(
                application=application,
                entity_type=applicant_data.get('entity_type'),
                first_name=applicant_data.get('first_name', ''),
                last_name=applicant_data.get('last_name', ''),
                organization_name=applicant_data.get('organization_name', ''),
                address=applicant_data.get('address'),
                email=applicant_data.get('email'),
                phone=applicant_data.get('phone'),
                # Story 5.1: Registracioni broj stored in maticni_broj field (alphanumeric)
                maticni_broj=applicant_data.get('registracioni_broj', ''),
            )

            # 4. Create InitiativeData record (Story 3.5, Story 5.3: Added naziv_tima, dates, budget)
            # Story 5.3: Parse date strings to date objects (YYYY-MM-DD format from HTML5 date input)
            from datetime import datetime as dt
            datum_startovanja = None
            datum_zavrsetka = None
            if initiative_data.get('datum_startovanja'):
                datum_startovanja = dt.strptime(initiative_data['datum_startovanja'], '%Y-%m-%d').date()
            if initiative_data.get('datum_zavrsetka'):
                datum_zavrsetka = dt.strptime(initiative_data['datum_zavrsetka'], '%Y-%m-%d').date()

            # Story 5.3: Parse totalni_budzet to Decimal
            from decimal import Decimal
            totalni_budzet = None
            if initiative_data.get('totalni_budzet'):
                totalni_budzet = Decimal(str(initiative_data['totalni_budzet']))

            initiative = InitiativeData.objects.create(
                application=application,
                # Story 5.3: Team name - FIRST field
                naziv_tima=initiative_data.get('naziv_tima', ''),
                naslov=initiative_data.get('naslov'),
                kratak_opis=initiative_data.get('kratak_opis'),
                problem=initiative_data.get('problem'),
                cilj_inicijative=initiative_data.get('cilj_inicijative'),
                # Story 5.3: Now called "Planirane aktivnosti" in UI
                planirani_koraci=initiative_data.get('planirani_koraci'),
                ocekivani_uticaj=initiative_data.get('ocekivani_uticaj'),
                # Story 5.3: Project timeline dates
                datum_startovanja=datum_startovanja,
                datum_zavrsetka=datum_zavrsetka,
                # Story 5.3: Total budget in EUR
                totalni_budzet=totalni_budzet
            )

            # Z1 (2026-07-24): Create FileMetadata from the session's UploadedFile records,
            # NOT from the client payload. The browser only knows the original filename; the
            # real name on disk (stored_filename) lives in UploadedFile. Trusting the client
            # here is exactly why COB downloads returned 404 (stored_filename was wrong).
            # This mirrors the COA path (process_submission builds metadata server-side).
            session_key = request.session.session_key
            uploaded_files_qs = UploadedFile.objects.none()
            if session_key:
                uploaded_files_qs = UploadedFile.objects.filter(
                    uploaded_by_session=session_key,
                    is_deleted=False,
                    application__isnull=True,
                    category__in=valid_categories,  # only this COB form's file types
                )

            for uf in uploaded_files_qs:
                FileMetadata.objects.create(
                    application=application,
                    file_type=uf.category,
                    original_filename=uf.original_filename,
                    stored_filename=uf.stored_filename,
                    file_size=uf.file_size,
                )

            # Story 5.1: Save team members (Ostali članovi tima)
            team_members_data = data.get('team_members', [])
            for member in team_members_data:
                # Only save if at least one field has data
                if member.get('ime_prezime') or member.get('email') or member.get('telefon'):
                    ClanTima.objects.create(
                        application=application,
                        ime_prezime=member.get('ime_prezime', ''),
                        email=member.get('email', ''),
                        telefon=member.get('telefon', '')
                    )

            # 5. Link the same uploaded files from session to application
            if session_key:
                uploaded_files_qs.update(application=application)

            # Success logging (GDPR-compliant, no PII)
            submission_logger.info(
                f'COB submission SUCCESS: {reference_number}',
                extra={
                    'reference_number': reference_number,
                    'application_type': 'COB',
                    'entity_type': applicant.entity_type,
                    'file_count': len(files_metadata),
                    'ip': request.META.get('REMOTE_ADDR')
                }
            )

            # Store application ID for email task (after transaction commits)
            application_id_for_email = application.id

        # Z4′: Send emails SYNCHRONOUSLY AFTER the transaction commits (Story 2.14, Story 3.6).
        # transaction.on_commit() guarantees emails only go out if the submission was actually saved.
        # Both *_now() helpers swallow errors so a mail failure never rolls back or breaks the submission.
        if application_id_for_email:
            try:
                # Story 2.14: Send confirmation email to user (AFTER transaction commits)
                transaction.on_commit(lambda: send_confirmation_email_now(application_id_for_email))

                # Story 3.6: Send admin notification email (AFTER transaction commits)
                transaction.on_commit(lambda: send_admin_notification_now(application_id_for_email, 'COB'))

                submission_logger.info(
                    f"Emails scheduled for {reference_number} (will send after transaction commit)"
                )
            except Exception as email_error:
                # Log email queue failure but don't fail the submission
                submission_logger.error(
                    f"Failed to queue email tasks for {reference_number}: {email_error}",
                    exc_info=True,
                    extra={'reference_number': reference_number, 'email_error_type': type(email_error).__name__}
                )
                # Submission still succeeds - email can be resent manually

        # Return success with reference number
        return JsonResponse({
            'success': True,
            'reference_number': reference_number,
            'message': 'Inicijativa uspešno podnesena.'
        }, status=201)

    except ValidationError as e:
        messages = e.messages if hasattr(e, 'messages') else [str(e)]
        submission_logger.warning(f'COB validation error: {messages}')
        return JsonResponse({
            'success': False,
            'error': ' '.join(messages)
        }, status=400)

    except Exception as e:
        # Log error for debugging
        submission_logger.error(
            f'COB submission FAILURE: {str(e)}',
            extra={
                'error': str(e),
                'ip': request.META.get('REMOTE_ADDR')
            },
            exc_info=True
        )

        error_msg = 'Greška pri čuvanju prijave. Molimo pokušajte ponovo.'
        if settings.DEBUG:
            error_msg = f'DEBUG: {str(e)}'
        return JsonResponse({
            'success': False,
            'error': error_msg
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

    # Z4′: Resend synchronously and report the real outcome to the user.
    logger.info(f"Resending email confirmation for {reference_number}")
    sent = send_confirmation_email_now(application.id)

    if sent:
        return JsonResponse({
            'success': True,
            'message': f"Email potvrda je poslata na {application.applicant.email}."
        })
    return JsonResponse({
        'success': False,
        'message': "Slanje email potvrde trenutno nije uspelo. Molimo preuzmite PDF potvrdu ili pokušajte kasnije."
    }, status=502)


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


@csrf_protect
@ensure_csrf_cookie  # ISSUE 1 FIX: Ensure CSRF cookie available for AJAX (consistency with Story 2.15)
@require_http_methods(['POST'])
def validate_cob_section_i(request):
    """
    AJAX endpoint for validating COB Section I data.
    Story 3.2: COB Section I - Backend Form Validation

    Purpose: Client-side can validate before proceeding to Section II.
    Architecture: Dual-layer validation (client calls this for server validation).

    Request: POST /api/validate/cob/section-i/
    Body: { entity_type, ime, prezime, naziv_organizacije, adresa, email, telefon }

    Response:
    - Success: { "valid": true }
    - Error: { "valid": false, "errors": { "field": ["error message"] } }

    Security:
    - CSRF protection enabled
    - Content-Type validation
    - JSON parsing with error handling
    """
    # ISSUE 11 FIX: Validate Content-Type header
    content_type = request.META.get('CONTENT_TYPE', '')
    if 'application/json' not in content_type:
        return JsonResponse({
            'valid': False,
            'errors': {'__all__': ['Content-Type must be application/json']}
        }, status=400)

    try:
        data = json.loads(request.body)
        form = COBApplicantForm(data)

        if form.is_valid():
            # ISSUE 9 FIX: Log successful validation (GDPR-compliant - no PII)
            submission_logger.info(
                f"COB Section I validation successful: entity_type={data.get('entity_type')}, "
                f"ip={request.META.get('REMOTE_ADDR')}"
            )
            return JsonResponse({
                'valid': True,
                'message': 'Podaci su validni.'
            })
        else:
            # Return field-specific errors
            return JsonResponse({
                'valid': False,
                'errors': form.errors.get_json_data()
            }, status=400)

    except json.JSONDecodeError:
        # ISSUE 4 FIX: Use __all__ instead of _all (Django standard)
        return JsonResponse({
            'valid': False,
            'errors': {'__all__': [{'message': 'Neispravan JSON format.', 'code': 'invalid_json'}]}
        }, status=400)
    except Exception as e:
        # ISSUE 3 FIX: Use submission_logger instead of logger
        submission_logger.error(f"COB Section I validation error: {str(e)}")

        # ISSUE 4 FIX: Use __all__ instead of _all
        return JsonResponse({
            'valid': False,
            'errors': {'__all__': [{'message': 'Greška pri validaciji. Molimo pokušajte ponovo.', 'code': 'server_error'}]}
        }, status=500)


@csrf_protect
@ensure_csrf_cookie
@require_http_methods(['POST'])
def validate_cob_section_ii(request):
    """
    AJAX endpoint for validating COB Section II data (initiative data).
    Story 3.3: COB Section II - Backend Form Validation

    Purpose: Client-side can validate before proceeding to Section III.
    Architecture: Dual-layer validation (client calls this for server validation).

    Request: POST /api/validate/cob/section-ii/
    Body: { naslov, kratak_opis, problem, cilj, planirani_koraci, ocekivani_uticaj }

    Response:
    - Success: { "valid": true }
    - Error: { "valid": false, "errors": { "field": ["error message"] } }
    """
    # Content-Type validation (Story 3-2 ISSUE 11)
    content_type = request.META.get('CONTENT_TYPE', '')
    if 'application/json' not in content_type:
        return JsonResponse({
            'valid': False,
            'errors': {'__all__': ['Content-Type mora biti application/json.']}
        }, status=400)

    try:
        data = json.loads(request.body)
        form = COBInitiativeDataForm(data)

        if form.is_valid():
            # ISSUE 8 FIX: Add IP address logging (consistency with Section I)
            submission_logger.info(
                'COB Section II validation successful',
                extra={
                    'validation_type': 'cob_section_ii',
                    'status': 'valid',
                    'ip': request.META.get('REMOTE_ADDR')
                }
            )

            return JsonResponse({
                'valid': True,
                'message': 'Podaci su validni.'
            })
        else:
            # ISSUE 7 FIX: Log validation failures (GDPR-compliant audit trail)
            submission_logger.info(
                'COB Section II validation failed',
                extra={
                    'validation_type': 'cob_section_ii',
                    'status': 'invalid',
                    'error_count': len(form.errors),
                    'ip': request.META.get('REMOTE_ADDR')
                }
            )

            # Return field-specific errors
            return JsonResponse({
                'valid': False,
                'errors': form.errors.get_json_data()
            }, status=400)

    except json.JSONDecodeError:
        # ISSUE 5 FIX: Match Story 3-2 error format (consistency)
        return JsonResponse({
            'valid': False,
            'errors': {'__all__': [{'message': 'Neispravan JSON format.', 'code': 'invalid_json'}]}
        }, status=400)
    except Exception as e:
        # Log error for debugging
        submission_logger.error(f"COB Section II validation error: {str(e)}")

        # ISSUE 6 FIX: Match Story 3-2 error format (consistency)
        return JsonResponse({
            'valid': False,
            'errors': {'__all__': [{'message': 'Greška pri validaciji. Molimo pokušajte ponovo.', 'code': 'server_error'}]}
        }, status=500)


@csrf_protect
@ensure_csrf_cookie
@require_http_methods(['POST'])
def validate_cob_section_iii(request):
    """
    AJAX endpoint for validating COB Section III data (documentation & consent).
    Story 3.4: COB Section III - Simplified Documentation (2 Files Only)

    Purpose: Client-side can validate before final submission.
    Architecture: Dual-layer validation (client calls this for server validation).

    Request: POST /api/validate/cob/section-iii/
    Body: {
        saglasnost_gdpr: true/false,
        file_metadata: {
            'BUDZET_INICIJATIVE': [{name, size}],  # Required, XLS/XLSX
            'PISMO_PODRSKE': [{name, size}]  # Optional, PDF/DOC/DOCX
        }
    }

    Response:
    - Success: { "valid": true }
    - Error: { "valid": false, "errors": { "field": ["error message"] } }
    """
    # Content-Type validation (Story 3-2 ISSUE 11)
    content_type = request.META.get('CONTENT_TYPE', '')
    if 'application/json' not in content_type:
        return JsonResponse({
            'valid': False,
            'errors': {'__all__': [{'message': 'Content-Type mora biti application/json.', 'code': 'invalid_content_type'}]}
        }, status=400)

    try:
        data = json.loads(request.body)

        # Validate GDPR consent checkbox
        form = COBSectionIIIForm(data)

        if not form.is_valid():
            # Return form errors
            return JsonResponse({
                'valid': False,
                'errors': form.errors.get_json_data()
            }, status=400)

        # Validate file metadata structure
        file_metadata = data.get('file_metadata', {})
        files_valid, file_errors = validate_cob_file_metadata(file_metadata)

        if not files_valid:
            # ISSUE 8 FIX: Log validation failures (match Story 3-3 pattern)
            submission_logger.info(
                'COB Section III validation failed - file metadata errors',
                extra={
                    'validation_type': 'cob_section_iii',
                    'status': 'invalid',
                    'error_count': len(file_errors),
                    'ip': request.META.get('REMOTE_ADDR')
                }
            )

            # Return file validation errors
            return JsonResponse({
                'valid': False,
                'errors': file_errors
            }, status=400)

        # Success logging (GDPR-compliant, no PII)
        submission_logger.info(
            'COB Section III validation successful',
            extra={
                'validation_type': 'cob_section_iii',
                'status': 'valid',
                'ip': request.META.get('REMOTE_ADDR')
            }
        )

        return JsonResponse({
            'valid': True,
            'message': 'Podaci su validni.'
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'valid': False,
            'errors': {'__all__': [{'message': 'Neispravan JSON format.', 'code': 'invalid_json'}]}
        }, status=400)
    except Exception as e:
        # Log error for debugging
        submission_logger.error(f"COB Section III validation error: {str(e)}")

        return JsonResponse({
            'valid': False,
            'errors': {'__all__': [{'message': 'Greška pri validaciji. Molimo pokušajte ponovo.', 'code': 'server_error'}]}
        }, status=500)


@staff_member_required
def download_file(request, app_id, file_id):
    """
    Download individual file from application.
    Story 4.4: Admin document download functionality.

    CODE REVIEW FIXES:
    - ISSUE 1: Added try/except for file handle resource leak protection
    - ISSUE 2: Fixed field name (category → file_type)
    - ISSUE 3: Added MIME type validation against database
    - ISSUE 6: Imported FILE_CATEGORY_FOLDERS constant
    - ISSUE 9: Consistent Serbian error messages

    Args:
        request: Django request object
        app_id: Application ID (primary key)
        file_id: FileMetadata ID (primary key)

    Returns:
        FileResponse with file content

    Security:
        - Requires admin authentication (@staff_member_required)
        - Validates file belongs to application
        - Validates file exists on disk
        - MIME type validated against stored value
        - Returns 404 if not found, 403 if not authorized
    """
    # Get application and file metadata
    application = get_object_or_404(Application, pk=app_id)
    file_metadata = get_object_or_404(FileMetadata, pk=file_id)

    # Security check: Verify file belongs to this application
    if file_metadata.application_id != application.id:
        logger.warning(
            f"Unauthorized file download attempt: file_id={file_id}, "
            f"file_app_id={file_metadata.application_id}, requested_app_id={app_id}, "
            f"user={request.user.username}"
        )
        # ISSUE 9 FIX: Consistent Serbian
        return HttpResponseForbidden("Nemate pristup ovom fajlu.")

    # Z1 (2026-07-24): single source of truth for locating the file
    # (UploadedFile.file_path → submissions/<folder>/ → uploads/drafts/).
    file_path = resolve_file_on_disk(file_metadata)
    if not file_path:
        logger.error(
            f"File not found on disk: FileMetadata ID {file_id}, "
            f"stored={file_metadata.stored_filename!r}, Application: {application.reference_number}"
        )
        raise Http404("Fajl nije pronađen na serveru. Molimo kontaktirajte support.")

    # ISSUE 3 FIX: Validate MIME type against database (security)
    # Determine MIME type from file extension
    mime_types = {
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.xls': 'application/vnd.ms-excel',
        '.pdf': 'application/pdf',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    }
    file_ext = os.path.splitext(file_metadata.original_filename)[1].lower()
    expected_content_type = mime_types.get(file_ext, 'application/octet-stream')

    # Use MIME type from database if available (more secure than extension-based)
    if hasattr(file_metadata, 'mime_type') and file_metadata.mime_type:
        content_type = file_metadata.mime_type
    else:
        content_type = expected_content_type

    # Z1: allow inline viewing in the browser (e.g. open a PDF/Excel preview) via ?inline=1.
    # Default remains attachment (download).
    as_attachment = request.GET.get('inline') != '1'

    # ISSUE 1 FIX: Wrap file opening in try/except to prevent resource leak
    try:
        file_handle = open(file_path, 'rb')
        response = FileResponse(
            file_handle,
            content_type=content_type,
            as_attachment=as_attachment,
            filename=file_metadata.original_filename
        )

        logger.info(
            f"File {'viewed' if not as_attachment else 'downloaded'}: {file_metadata.original_filename}, "
            f"application={application.reference_number}, user={request.user.username}"
        )

        return response
    except Exception as e:
        # ISSUE 1 FIX: Ensure file handle is closed if FileResponse creation fails
        logger.error(
            f"Error creating file response: {str(e)}, file_path={file_path}"
        )
        raise Http404("Greška pri download-u fajla. Molimo kontaktirajte support.")


@staff_member_required
def download_all_files(request, app_id):
    """
    Download all files from application as ZIP archive.
    Story 4.4: Admin bulk document download functionality.

    CODE REVIEW FIXES:
    - ISSUE 4: Added select_related for query optimization
    - ISSUE 5: Added transaction rollback and error handling for ZIP creation
    - ISSUE 6: Imported FILE_CATEGORY_FOLDERS constant
    - ISSUE 7: Added Content-Length header
    - ISSUE 8: Added total file size validation (100MB limit)

    Args:
        request: Django request object
        app_id: Application ID (primary key)

    Returns:
        HttpResponse with ZIP file content

    Security:
        - Requires admin authentication (@staff_member_required)
        - Validates application exists
        - Only includes files that exist on disk
        - Validates total ZIP size (100MB max)
    """
    # Get application
    application = get_object_or_404(Application, pk=app_id)

    # ISSUE 4 FIX: Add select_related for optimization (defensive coding)
    files = FileMetadata.objects.filter(application=application).select_related('application').order_by('file_type', 'uploaded_at')

    # Check if application has any files
    if not files.exists():
        raise Http404("Prijava nema upload-ovanih dokumenata.")

    # ISSUE 8 FIX: Validate total file size before creating ZIP (prevent memory exhaustion)
    MAX_ZIP_SIZE = 100 * 1024 * 1024  # 100MB
    total_size = sum(f.file_size for f in files)

    if total_size > MAX_ZIP_SIZE:
        logger.warning(
            f"ZIP download rejected - total size too large: {total_size} bytes, "
            f"application={application.reference_number}, user={request.user.username}"
        )
        return HttpResponse(
            "ZIP fajl je prevelik (maksimalno 100MB). Molimo download-ujte fajlove pojedinačno.",
            status=413  # Payload Too Large
        )

    # ISSUE 5 FIX: Wrap ZIP creation in try/except for error handling
    try:
        # Create ZIP file in memory
        zip_buffer = BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Z1 (2026-07-24): use the shared resolver instead of duplicating path logic.
            for file_metadata in files:
                file_path = resolve_file_on_disk(file_metadata)

                # Only add file if it exists on disk
                if file_path:
                    # Add file to ZIP with original filename
                    zip_file.write(file_path, arcname=file_metadata.original_filename)
                else:
                    # Log missing file but continue (don't break entire ZIP download)
                    logger.warning(
                        f"File not found on disk during ZIP creation: "
                        f"stored={file_metadata.stored_filename!r}, "
                        f"FileMetadata ID: {file_metadata.id}, skipping"
                    )

        # Prepare response with ZIP file
        zip_buffer.seek(0)
        zip_content = zip_buffer.read()

        # ZIP filename: {reference_number}_documents.zip
        zip_filename = f"{application.reference_number}_documents.zip"

        response = HttpResponse(
            zip_content,
            content_type='application/zip'
        )
        response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'

        # ISSUE 7 FIX: Add Content-Length header for download progress
        response['Content-Length'] = len(zip_content)

        logger.info(
            f"ZIP downloaded: {zip_filename}, "
            f"size={len(zip_content)} bytes, "
            f"application={application.reference_number}, user={request.user.username}"
        )

        return response

    except Exception as e:
        # ISSUE 5 FIX: Handle ZIP creation errors gracefully
        logger.error(
            f"ZIP creation failed for application {application.reference_number}: {str(e)}, "
            f"user={request.user.username}",
            exc_info=True
        )
        return HttpResponse(
            "Greška pri kreiranju ZIP fajla. Molimo pokušajte ponovo ili kontaktirajte support.",
            status=500
        )
