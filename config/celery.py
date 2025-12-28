"""
Celery configuration for DOMOVIK project.

Handles async email sending with Redis broker.
Story 2.14: Email Confirmation with Celery
"""
import os
from celery import Celery

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Create Celery app
app = Celery('domovik')

# Load config from Django settings (namespace 'CELERY')
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all installed apps
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to verify Celery is working."""
    print(f'Request: {self.request!r}')
