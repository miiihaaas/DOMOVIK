# -*- coding: utf-8 -*-
"""
DOMOVIK Admin API using Django Ninja.
Story 4.5: RESTful API for admin operations.

Endpoints:
- GET /api/admin/applications/ - List all applications (paginated, filtered)
- GET /api/admin/applications/<reference_number>/ - Get application detail
- PATCH /api/admin/applications/<reference_number>/ - Update application status
- GET /api/admin/applications/<reference_number>/files/<file_id>/download/ - Download single file
- GET /api/admin/applications/<reference_number>/files/download_all/ - Download all files as ZIP

Authentication: Django session-based (reuses admin session)
Authorization: Requires admin user (is_staff=True)
"""

from typing import List, Optional
from urllib.parse import urlencode
import logging

from ninja import NinjaAPI, Query
from ninja.errors import HttpError
from django.shortcuts import get_object_or_404
from django.http import HttpRequest, Http404
from django.core.paginator import Paginator

from apps.submissions.models import Application, FileMetadata

# Configure logging for API
logger = logging.getLogger(__name__)
from apps.submissions.schemas import (
    ApplicationListItemSchema,
    PaginatedApplicationListSchema,
    ApplicationDetailSchema,
    UpdateStatusSchema,
    UpdateStatusResponseSchema,
)
from apps.submissions.views import download_file, download_all_files
from apps.submissions.services import log_admin_action
from apps.submissions.constants import (
    ADMIN_ACTION_API_VIEWED,
    ADMIN_ACTION_API_STATUS_CHANGE,
    ADMIN_ACTION_API_DOWNLOADED_FILE,
    ADMIN_ACTION_API_DOWNLOADED_ALL,
)


# ============================================================================
# Custom Authentication
# ============================================================================

class AdminAuth:
    """
    Custom authentication for admin API.
    Requires authenticated user with is_staff=True.
    """
    def __call__(self, request: HttpRequest):
        if request.user.is_authenticated and request.user.is_staff:
            return request.user
        return None


# ============================================================================
# API Instance
# ============================================================================

api = NinjaAPI(
    title="DOMOVIK Admin API",
    version="1.0.0",
    description="RESTful API for DOMOVIK admin panel operations",
    auth=AdminAuth(),  # Global authentication for all endpoints
    csrf=True,  # Enable CSRF protection (required for PATCH)
)


# ============================================================================
# Constants
# ============================================================================

DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100
VALID_APPLICATION_TYPES = {'COA', 'COB'}
VALID_STATUSES = {'submitted', 'under_review', 'approved', 'rejected'}


# ============================================================================
# Helper Functions
# ============================================================================

def get_applicant_name(applicant) -> str:
    """
    Get display name for applicant.

    Returns:
        Full name for fizicko lice or organization name for pravno lice
    """
    if applicant.entity_type == 'fizicko':
        return f"{applicant.first_name} {applicant.last_name}"
    else:
        return applicant.organization_name


def get_application_title(application) -> str:
    """
    Get title from project_data or initiative_data.

    Returns:
        Project/initiative title, or 'N/A' if data missing
    """
    if application.application_type == 'COA' and hasattr(application, 'project_data'):
        return application.project_data.title  # ProjectData uses English field names
    elif application.application_type == 'COB' and hasattr(application, 'initiative_data'):
        return application.initiative_data.naslov  # InitiativeData uses Serbian field names
    return "N/A"


# ============================================================================
# List Applications Endpoint
# ============================================================================

@api.get(
    "/applications/",
    response=PaginatedApplicationListSchema,
    summary="List all applications",
    tags=["Applications"]
)
def list_applications(
    request: HttpRequest,
    type: Optional[str] = Query(None, description="Filter by type: COA or COB"),
    status: Optional[str] = Query(None, description="Filter by status: submitted, under_review, approved, rejected"),
    page: int = Query(1, ge=1, description="Page number (starts at 1)"),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description=f"Items per page (max {MAX_PAGE_SIZE})"),
):
    """
    Get paginated list of all applications with filtering.

    Query Parameters:
    - type: Filter by application type (COA or COB)
    - status: Filter by status (submitted, under_review, approved, rejected)
    - page: Page number (default: 1)
    - page_size: Items per page (default: 25, max: 100)

    Returns:
    - Paginated list of applications with basic info
    """
    try:
        # Input validation for filter parameters
        if type and type.upper() not in VALID_APPLICATION_TYPES:
            logger.warning(f"Invalid type filter: {type}")
            raise HttpError(400, f"Invalid type filter. Must be one of: {', '.join(VALID_APPLICATION_TYPES)}")

        if status and status.lower() not in VALID_STATUSES:
            logger.warning(f"Invalid status filter: {status}")
            raise HttpError(400, f"Invalid status filter. Must be one of: {', '.join(VALID_STATUSES)}")

        # Base queryset with optimization
        queryset = Application.objects.select_related(
            'applicant', 'project_data', 'initiative_data'
        ).all()

        # Apply filters
        if type:
            queryset = queryset.filter(application_type=type.upper())
        if status:
            queryset = queryset.filter(status=status.lower())

        # Pagination
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)

        # Build response using list comprehension (more efficient than loop)
        results = [
            ApplicationListItemSchema(
                reference_number=app.reference_number,
                applicant_name=get_applicant_name(app.applicant),
                title=get_application_title(app),
                type=app.application_type,
                status=app.status,
                submitted_at=app.submitted_at,
            )
            for app in page_obj.object_list
        ]

        # Build pagination links with proper URL encoding
        base_url = request.build_absolute_uri(request.path)

        def build_pagination_url(page_num: int) -> str:
            """Build pagination URL preserving all query parameters."""
            params = {'page': page_num, 'page_size': page_size}
            if type:
                params['type'] = type
            if status:
                params['status'] = status
            return f"{base_url}?{urlencode(params)}"

        next_url = build_pagination_url(page_obj.next_page_number()) if page_obj.has_next() else None
        prev_url = build_pagination_url(page_obj.previous_page_number()) if page_obj.has_previous() else None

        logger.info(f"List applications: page={page}, page_size={page_size}, count={paginator.count}, filters={{type={type}, status={status}}}")

        return PaginatedApplicationListSchema(
            count=paginator.count,
            next=next_url,
            previous=prev_url,
            results=results,
        )
    except HttpError:
        raise
    except Exception as e:
        logger.error(f"Error listing applications: {str(e)}", exc_info=True)
        raise HttpError(500, "Internal server error while listing applications")


# ============================================================================
# Application Detail Endpoint
# ============================================================================

@api.get(
    "/applications/{reference_number}/",
    response=ApplicationDetailSchema,
    summary="Get application detail",
    tags=["Applications"]
)
def get_application_detail(request: HttpRequest, reference_number: str):
    """
    Get complete details for a single application.

    Path Parameters:
    - reference_number: Application reference number (e.g., COA-2025-001)

    Returns:
    - Complete application data including applicant, project/initiative data, and files
    """
    try:
        # Get application with all related data
        try:
            application = Application.objects.select_related(
                'applicant', 'project_data', 'initiative_data'
            ).prefetch_related('files').get(reference_number=reference_number)
        except Application.DoesNotExist:
            logger.warning(f"Application not found: {reference_number}")
            raise HttpError(404, f"Application with reference number '{reference_number}' not found")

        # Log API view action (Story 4.6)
        log_admin_action(
            user=request.user,
            action=ADMIN_ACTION_API_VIEWED,
            application=application,
            request=request,
        )

        # Build response using Pydantic schema
        # Pydantic automatically handles ORM conversion with from_attributes=True
        logger.info(f"Retrieved application detail: {reference_number}")
        return ApplicationDetailSchema.model_validate(application)
    except HttpError:
        raise
    except Exception as e:
        logger.error(f"Error retrieving application detail: {str(e)}", exc_info=True)
        raise HttpError(500, "Internal server error while retrieving application details")


# ============================================================================
# Update Application Status Endpoint
# ============================================================================

@api.patch(
    "/applications/{reference_number}/",
    response=UpdateStatusResponseSchema,
    summary="Update application status",
    tags=["Applications"]
)
def update_application_status(
    request: HttpRequest,
    reference_number: str,
    payload: UpdateStatusSchema
):
    """
    Update the status of an application.

    Path Parameters:
    - reference_number: Application reference number (e.g., COA-2025-001)

    Request Body:
    - status: New status (submitted, under_review, approved, rejected)

    Returns:
    - Success confirmation and updated application data
    """
    try:
        # Get application
        try:
            application = Application.objects.select_related(
                'applicant', 'project_data', 'initiative_data'
            ).prefetch_related('files').get(reference_number=reference_number)
        except Application.DoesNotExist:
            logger.warning(f"Application not found for status update: {reference_number}")
            raise HttpError(404, f"Application with reference number '{reference_number}' not found")

        # Update status
        old_status = application.status
        application.status = payload.status
        application.save(update_fields=['status'])  # Application has no updated_at field

        # Log status change with old → new transition (Story 4.6)
        log_admin_action(
            user=request.user,
            action=ADMIN_ACTION_API_STATUS_CHANGE,
            application=application,
            old_value=old_status,
            new_value=payload.status,
            request=request,
        )

        logger.info(f"Status updated: {reference_number} from '{old_status}' to '{payload.status}' by user {request.user.username}")

        # Build response
        return UpdateStatusResponseSchema(
            success=True,
            message=f"Status updated from '{old_status}' to '{payload.status}'",
            updated_application=ApplicationDetailSchema.model_validate(application)
        )
    except HttpError:
        raise
    except Exception as e:
        logger.error(f"Error updating application status: {str(e)}", exc_info=True)
        raise HttpError(500, "Internal server error while updating application status")


# ============================================================================
# File Download Endpoints
# ============================================================================

@api.get(
    "/applications/{reference_number}/files/{int:file_id}/download/",
    summary="Download single file",
    tags=["Files"],
    auth=AdminAuth(),  # Explicit auth (though global auth also applies)
)
def api_download_file(request: HttpRequest, reference_number: str, file_id: int):
    """
    Download a single file from an application.

    Path Parameters:
    - reference_number: Application reference number (e.g., COA-2025-001)
    - file_id: File metadata ID

    Returns:
    - File as binary stream with original filename

    Security:
    - Requires admin authentication
    - Validates file belongs to application
    - Returns 404 if file not found
    """
    try:
        # Get application to validate reference_number
        try:
            application = Application.objects.get(reference_number=reference_number)
        except Application.DoesNotExist:
            logger.warning(f"Application not found for file download: {reference_number}")
            raise HttpError(404, f"Application with reference number '{reference_number}' not found")

        # Get file metadata for logging (Story 4.6)
        try:
            file_metadata = FileMetadata.objects.get(pk=file_id, application=application)
        except FileMetadata.DoesNotExist:
            logger.warning(f"File not found: file_id={file_id}, application={reference_number}")
            raise HttpError(404, f"File with ID {file_id} not found for application {reference_number}")

        # Log API download action BEFORE delegating to view (Story 4.6)
        # This is the SINGLE logging point for all downloads (prevents double-logging)
        log_admin_action(
            user=request.user,
            action=ADMIN_ACTION_API_DOWNLOADED_FILE,
            application=application,
            old_value=file_metadata.original_filename,  # Log which file was downloaded
            request=request,
        )

        # Delegate to existing download_file view from Story 4.4
        # This reuses all security checks and error handling
        logger.info(f"File download requested: file_id={file_id}, application={reference_number}, user={request.user.username}")
        return download_file(request, application.id, file_id)
    except HttpError:
        raise
    except Http404 as e:
        # Convert Django Http404 to Ninja HttpError
        logger.warning(f"File not found: {str(e)}")
        raise HttpError(404, str(e))
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}", exc_info=True)
        raise HttpError(500, "Internal server error while downloading file")


@api.get(
    "/applications/{reference_number}/files/download_all/",
    summary="Download all files as ZIP",
    tags=["Files"],
    auth=AdminAuth(),
)
def api_download_all_files(request: HttpRequest, reference_number: str):
    """
    Download all files from an application as a ZIP archive.

    Path Parameters:
    - reference_number: Application reference number (e.g., COA-2025-001)

    Returns:
    - ZIP file with all documents, named {reference_number}_documents.zip

    Security:
    - Requires admin authentication
    - Returns 404 if application has no files
    """
    try:
        # Get application to validate reference_number
        try:
            application = Application.objects.get(reference_number=reference_number)
        except Application.DoesNotExist:
            logger.warning(f"Application not found for bulk download: {reference_number}")
            raise HttpError(404, f"Application with reference number '{reference_number}' not found")

        # Count files for logging (Story 4.6)
        file_count = application.files.count()

        # Log API download all action BEFORE delegating to view (Story 4.6)
        # This is the SINGLE logging point for all downloads (prevents double-logging)
        log_admin_action(
            user=request.user,
            action=ADMIN_ACTION_API_DOWNLOADED_ALL,
            application=application,
            old_value=f"{file_count} files",  # Log how many files were downloaded
            request=request,
        )

        # Delegate to existing download_all_files view from Story 4.4
        logger.info(f"Bulk file download requested: application={reference_number}, user={request.user.username}")
        return download_all_files(request, application.id)
    except HttpError:
        raise
    except Http404 as e:
        # Convert Django Http404 to Ninja HttpError
        logger.warning(f"Files not found for bulk download: {str(e)}")
        raise HttpError(404, str(e))
    except Exception as e:
        logger.error(f"Error downloading all files: {str(e)}", exc_info=True)
        raise HttpError(500, "Internal server error while downloading files")
