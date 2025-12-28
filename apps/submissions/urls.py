# -*- coding: utf-8 -*-
"""
URL configuration for submissions app.
Story 2.8: File upload/delete API endpoints
Story 2.11: Submission processing endpoint
Story 2.13: Success screen, PDF download, email resend
Story 2.15: Draft registration and expiration check API endpoints
Story 3.1: COB routing and form initialization
Story 3.2: COB Section I validation API endpoint
"""
from django.urls import path
from apps.submissions import views

app_name = 'submissions'

urlpatterns = [
    # COA - Projekat (Epic 2)
    path('projekat/', views.ProjectApplicationView.as_view(), name='coa_form'),

    # COB - Inicijativa (Epic 3 - Story 3.1)
    path('inicijativa/', views.cob_form, name='cob_form'),

    # File upload/delete endpoints (Story 2.8)
    path('upload/', views.upload_file, name='upload_file'),
    path('delete/<int:file_id>/', views.delete_file, name='delete_file'),

    # Submission endpoint (Story 2.11)
    path('submit/', views.submit_application, name='submit_application'),

    # Success screen (Story 2.13)
    path('success/<str:application_type>/<str:reference_number>/',
         views.success_screen,
         name='success_screen'),

    # PDF download (Story 2.13)
    path('download-pdf/<str:reference_number>/',
         views.download_pdf_confirmation,
         name='download_pdf'),

    # Email resend (Story 2.13)
    path('resend-email/<str:reference_number>/',
         views.resend_email,
         name='resend_email'),

    # Draft management endpoints (Story 2.15)
    path('api/drafts/register/', views.register_draft, name='register_draft'),
    path('api/drafts/check/<uuid:draft_id>/', views.check_draft_expiration, name='check_draft_expiration'),

    # COB validation API (Story 3.2, 3.3)
    path('api/validate/cob/section-i/', views.validate_cob_section_i, name='validate_cob_section_i'),
    path('api/validate/cob/section-ii/', views.validate_cob_section_ii, name='validate_cob_section_ii'),
]
