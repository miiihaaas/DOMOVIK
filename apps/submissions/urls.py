# -*- coding: utf-8 -*-
"""
URL configuration for submissions app.
Story 2.8: File upload/delete API endpoints
"""
from django.urls import path
from apps.submissions import views

app_name = 'submissions'

urlpatterns = [
    # File upload/delete endpoints (Story 2.8)
    path('upload/', views.upload_file, name='upload_file'),
    path('delete/<int:file_id>/', views.delete_file, name='delete_file'),
]
