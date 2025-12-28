"""
Import Celery app to ensure it's loaded when Django starts.
Story 2.14: Email Confirmation with Celery
"""
from .celery import app as celery_app

__all__ = ('celery_app',)
