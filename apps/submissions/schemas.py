# -*- coding: utf-8 -*-
"""
Pydantic schemas for DOMOVIK Admin API.
Story 4.5: RESTful API for admin operations.

Uses Pydantic for automatic validation, serialization, and OpenAPI schema generation.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ============================================================================
# File Metadata Schemas
# ============================================================================

class FileMetadataSchema(BaseModel):
    """Schema for file metadata in API responses."""
    id: int = Field(..., description="File metadata ID", example=1)
    file_type: str = Field(..., description="File type category", example="BUDGET")
    original_filename: str = Field(..., description="Original filename", example="Budzet_Projekta.xlsx")
    stored_filename: str = Field(..., description="Stored filename (UUID-based)", example="COA-2025-001_budzet_abc123.xlsx")
    file_size: int = Field(..., description="File size in bytes", example=10240)
    uploaded_at: datetime = Field(..., description="Upload timestamp", example="2025-12-30T10:00:00Z")

    class Config:
        from_attributes = True  # Pydantic v2: Enable ORM mode


# ============================================================================
# Application List Schemas
# ============================================================================

class ApplicationListItemSchema(BaseModel):
    """Schema for individual application in list endpoint."""
    reference_number: str = Field(..., description="Unique application reference number", example="COA-2025-001")
    applicant_name: str = Field(..., description="Applicant full name or organization name", example="Marko Petrović")
    title: str = Field(..., description="Project or initiative title", example="Community Center Renovation")
    type: str = Field(..., description="Application type: COA or COB", example="COA")
    status: str = Field(..., description="Current status", example="submitted")
    submitted_at: Optional[datetime] = Field(None, description="Submission timestamp", example="2025-12-30T10:00:00Z")

    class Config:
        from_attributes = True


class PaginatedApplicationListSchema(BaseModel):
    """Schema for paginated application list response."""
    count: int
    next: Optional[str]
    previous: Optional[str]
    results: List[ApplicationListItemSchema]


# ============================================================================
# Applicant Schemas
# ============================================================================

class ApplicantSchema(BaseModel):
    """Schema for applicant data."""
    entity_type: str  # 'fizicko' or 'pravno'
    # Fizičko lice fields
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    jmbg: Optional[str] = None
    # Pravno lice fields
    organization_name: Optional[str] = None
    registration_number: Optional[str] = None
    # Shared fields
    address: str
    email: str
    phone: str

    class Config:
        from_attributes = True


# ============================================================================
# Project/Initiative Data Schemas
# ============================================================================

class ProjectDataSchema(BaseModel):
    """Schema for COA project data."""
    title: str
    short_description: str
    problem: str
    main_goal: str
    specific_goals: str
    target_groups: str
    activities: str
    results: str
    total_budget: int  # IntegerField in model

    class Config:
        from_attributes = True


class InitiativeDataSchema(BaseModel):
    """Schema for COB initiative data."""
    naslov: str
    kratak_opis: str
    problem: str
    cilj_inicijative: str  # Note: Model field is cilj_inicijative not cilj
    planirani_koraci: str
    ocekivani_uticaj: str

    class Config:
        from_attributes = True


# ============================================================================
# Application Detail Schema
# ============================================================================

class ApplicationDetailSchema(BaseModel):
    """Schema for complete application detail endpoint."""
    reference_number: str
    application_type: str  # 'COA' or 'COB'
    status: str
    created_at: datetime
    submitted_at: Optional[datetime] = None  # Can be NULL until submitted
    applicant: ApplicantSchema
    project_data: Optional[ProjectDataSchema] = None  # COA only
    initiative_data: Optional[InitiativeDataSchema] = None  # COB only
    files: List[FileMetadataSchema]

    class Config:
        from_attributes = True

    @classmethod
    def model_validate(cls, obj, **kwargs):
        """
        Custom validation to handle Django querysets and relationships.

        Handles:
        - Django RelatedManager for files (converts to list)
        - Optional project_data/initiative_data (only one exists per application)
        - Validates applicant relationship exists
        """
        try:
            # Validate required relationships exist
            if not hasattr(obj, 'applicant'):
                raise ValueError(f"Application {obj.reference_number} missing required applicant relationship")

            # Build dict manually to handle Django relationships
            # NOTE: files queryset limited to 100 to prevent memory exhaustion
            files_qs = obj.files.all()[:100] if hasattr(obj, 'files') else []

            data = {
                'reference_number': obj.reference_number,
                'application_type': obj.application_type,
                'status': obj.status,
                'created_at': obj.created_at,
                'submitted_at': obj.submitted_at,
                'applicant': obj.applicant,
                'project_data': getattr(obj, 'project_data', None),
                'initiative_data': getattr(obj, 'initiative_data', None),
                'files': list(files_qs),
            }
            return super().model_validate(data, **kwargs)
        except Exception as e:
            raise ValueError(f"Failed to validate ApplicationDetailSchema: {str(e)}")


# ============================================================================
# Update Status Schemas
# ============================================================================

class UpdateStatusSchema(BaseModel):
    """Schema for PATCH /api/admin/applications/<ref>/ request."""
    status: str = Field(
        ...,
        description="New status for application",
        pattern="^(submitted|under_review|approved|rejected)$"
    )


class UpdateStatusResponseSchema(BaseModel):
    """Schema for PATCH /api/admin/applications/<ref>/ response."""
    success: bool
    message: str
    updated_application: ApplicationDetailSchema
