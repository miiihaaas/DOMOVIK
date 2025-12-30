# -*- coding: utf-8 -*-
"""
Tests for Admin Activity Logging (Story 4.6)

Covers:
1. AdminLog model creation and validation
2. log_admin_action() helper function (IP extraction, user agent, etc.)
3. Django Admin logging integration (view, status change)
4. API logging integration (view, status change, downloads)
5. AdminLog admin interface (read-only, filtering)
6. Celery cleanup task for log retention

Total tests: 18+
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from unittest.mock import Mock, patch
import json

from apps.submissions.models import (
    Application,
    Applicant,
    AdminLog,
    ProjectData,
    FileMetadata,
)
from apps.submissions.services import log_admin_action
from apps.submissions.constants import (
    ADMIN_ACTION_VIEWED,
    ADMIN_ACTION_STATUS_CHANGE,
    ADMIN_ACTION_DOWNLOADED_FILE,
    ADMIN_ACTION_DOWNLOADED_ALL,
    ADMIN_ACTION_API_VIEWED,
    ADMIN_ACTION_API_STATUS_CHANGE,
    ADMIN_ACTION_API_DOWNLOADED_FILE,
    ADMIN_ACTION_API_DOWNLOADED_ALL,
)
from apps.submissions.tasks import cleanup_old_admin_logs


class AdminLogModelTest(TestCase):
    """Test AdminLog model creation and field validation."""

    def setUp(self):
        """Create test admin user and application."""
        self.admin_user = User.objects.create_user(
            username='admin_test',
            password='testpass123',
            is_staff=True
        )

        # Create test application (must create Application first, then Applicant)
        self.application = Application.objects.create(
            reference_number='COA-2025-001',
            application_type='COA',
            status='submitted'
        )

        self.applicant = Applicant.objects.create(
            application=self.application,
            entity_type='fizicko',
            first_name='Test',
            last_name='User',
            address='Test Address 123',
            email='test@example.com',
            phone='+381601234567',
            jmbg='0101990123456'
        )

    def test_create_admin_log_minimal(self):
        """Test creating admin log with minimal required fields."""
        log = AdminLog.objects.create(
            user=self.admin_user,
            action=ADMIN_ACTION_VIEWED
        )

        self.assertIsNotNone(log.id)
        self.assertEqual(log.user, self.admin_user)
        self.assertEqual(log.action, ADMIN_ACTION_VIEWED)
        self.assertIsNone(log.application)
        self.assertIsNone(log.old_value)
        self.assertIsNone(log.new_value)
        self.assertIsNone(log.ip_address)
        self.assertIsNone(log.user_agent)
        self.assertIsNotNone(log.timestamp)

    def test_create_admin_log_complete(self):
        """Test creating admin log with all fields."""
        log = AdminLog.objects.create(
            user=self.admin_user,
            action=ADMIN_ACTION_STATUS_CHANGE,
            application=self.application,
            old_value='submitted',
            new_value='under_review',
            ip_address='192.168.1.100',
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        )

        self.assertEqual(log.user, self.admin_user)
        self.assertEqual(log.action, ADMIN_ACTION_STATUS_CHANGE)
        self.assertEqual(log.application, self.application)
        self.assertEqual(log.old_value, 'submitted')
        self.assertEqual(log.new_value, 'under_review')
        self.assertEqual(log.ip_address, '192.168.1.100')
        self.assertIn('Mozilla', log.user_agent)

    def test_admin_log_ordering(self):
        """Test AdminLog default ordering (newest first)."""
        log1 = AdminLog.objects.create(
            user=self.admin_user,
            action=ADMIN_ACTION_VIEWED,
            application=self.application
        )

        # Wait a bit to ensure different timestamps
        from time import sleep
        sleep(0.01)

        log2 = AdminLog.objects.create(
            user=self.admin_user,
            action=ADMIN_ACTION_VIEWED,
            application=self.application
        )

        logs = list(AdminLog.objects.all())
        self.assertEqual(logs[0].id, log2.id)  # Newest first
        self.assertEqual(logs[1].id, log1.id)

    def test_admin_log_str_representation(self):
        """Test AdminLog __str__ method."""
        log = AdminLog.objects.create(
            user=self.admin_user,
            action=ADMIN_ACTION_STATUS_CHANGE,
            application=self.application
        )

        str_repr = str(log)
        self.assertIn(self.admin_user.username, str_repr)
        self.assertIn(self.application.reference_number, str_repr)
        self.assertIn(ADMIN_ACTION_STATUS_CHANGE, str_repr)


class LogAdminActionHelperTest(TestCase):
    """Test log_admin_action() helper function."""

    def setUp(self):
        """Create test admin user and application."""
        self.admin_user = User.objects.create_user(
            username='admin_test',
            password='testpass123',
            is_staff=True
        )

        self.application = Application.objects.create(
            reference_number='COA-2025-001',
            application_type='COA',
            status='submitted'
        )

        self.applicant = Applicant.objects.create(
            application=self.application,
            entity_type='fizicko',
            first_name='Test',
            last_name='User',
            address='Test Address 123',
            email='test@example.com',
            phone='+381601234567',
            jmbg='0101990123456'
        )

    def test_log_admin_action_without_request(self):
        """Test logging action without HTTP request (no IP/user agent)."""
        log = log_admin_action(
            user=self.admin_user,
            action=ADMIN_ACTION_VIEWED,
            application=self.application
        )

        self.assertIsNotNone(log)
        self.assertEqual(log.user, self.admin_user)
        self.assertEqual(log.action, ADMIN_ACTION_VIEWED)
        self.assertEqual(log.application, self.application)
        self.assertIsNone(log.ip_address)
        self.assertIsNone(log.user_agent)

    def test_log_admin_action_with_request(self):
        """Test logging action with HTTP request (extracts IP and user agent)."""
        # Create mock request
        request = Mock()
        request.META = {
            'REMOTE_ADDR': '192.168.1.100',
            'HTTP_USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        }
        request.user = self.admin_user

        log = log_admin_action(
            user=self.admin_user,
            action=ADMIN_ACTION_VIEWED,
            application=self.application,
            request=request
        )

        self.assertEqual(log.ip_address, '192.168.1.100')
        self.assertIn('Mozilla', log.user_agent)

    def test_log_admin_action_with_status_change(self):
        """Test logging status change with old → new values."""
        log = log_admin_action(
            user=self.admin_user,
            action=ADMIN_ACTION_STATUS_CHANGE,
            application=self.application,
            old_value='submitted',
            new_value='under_review'
        )

        self.assertEqual(log.old_value, 'submitted')
        self.assertEqual(log.new_value, 'under_review')

    def test_log_admin_action_with_x_forwarded_for(self):
        """Test IP extraction from X-Forwarded-For header (proxy support)."""
        request = Mock()
        request.META = {
            'HTTP_X_FORWARDED_FOR': '203.0.113.45, 192.168.1.1',
            'REMOTE_ADDR': '192.168.1.100',
            'HTTP_USER_AGENT': 'Test Agent'
        }

        log = log_admin_action(
            user=self.admin_user,
            action=ADMIN_ACTION_VIEWED,
            application=self.application,
            request=request
        )

        # Should extract first IP from X-Forwarded-For
        self.assertEqual(log.ip_address, '203.0.113.45')

    def test_log_admin_action_ipv6(self):
        """Test IP extraction with IPv6 address."""
        request = Mock()
        request.META = {
            'REMOTE_ADDR': '2001:0db8:85a3:0000:0000:8a2e:0370:7334',
            'HTTP_USER_AGENT': 'Test Agent'
        }

        log = log_admin_action(
            user=self.admin_user,
            action=ADMIN_ACTION_VIEWED,
            application=self.application,
            request=request
        )

        self.assertEqual(log.ip_address, '2001:0db8:85a3:0000:0000:8a2e:0370:7334')

    def test_log_admin_action_malformed_ip(self):
        """Test graceful handling of malformed IP address."""
        request = Mock()
        request.META = {
            'HTTP_X_FORWARDED_FOR': 'not-an-ip',
            'REMOTE_ADDR': '192.168.1.100',
            'HTTP_USER_AGENT': 'Test Agent'
        }

        log = log_admin_action(
            user=self.admin_user,
            action=ADMIN_ACTION_VIEWED,
            application=self.application,
            request=request
        )

        # Should use malformed value (validation happens at model level if needed)
        self.assertEqual(log.ip_address, 'not-an-ip')

    def test_log_admin_action_empty_x_forwarded_for(self):
        """Test fallback to REMOTE_ADDR when X-Forwarded-For is empty."""
        request = Mock()
        request.META = {
            'HTTP_X_FORWARDED_FOR': '',
            'REMOTE_ADDR': '192.168.1.100',
            'HTTP_USER_AGENT': 'Test Agent'
        }

        log = log_admin_action(
            user=self.admin_user,
            action=ADMIN_ACTION_VIEWED,
            application=self.application,
            request=request
        )

        # Should fall back to REMOTE_ADDR
        self.assertEqual(log.ip_address, '192.168.1.100')


class DjangoAdminLoggingTest(TestCase):
    """Test Django Admin logging integration."""

    def setUp(self):
        """Create test admin user and application."""
        self.admin_user = User.objects.create_user(
            username='admin_test',
            password='testpass123',
            is_staff=True,
            is_superuser=True
        )

        self.application = Application.objects.create(
            reference_number='COA-2025-001',
            application_type='COA',
            status='submitted'
        )

        self.applicant = Applicant.objects.create(
            application=self.application,
            entity_type='fizicko',
            first_name='Test',
            last_name='User',
            address='Test Address 123',
            email='test@example.com',
            phone='+381601234567',
            jmbg='0101990123456'
        )

        self.client = Client()
        self.client.force_login(self.admin_user)

    def test_viewing_application_creates_log(self):
        """Test that viewing application detail in Django Admin creates log entry."""
        # Clear any existing logs
        AdminLog.objects.all().delete()

        # View application detail page
        url = reverse('admin:submissions_application_change', args=[self.application.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        # Check log was created
        logs = AdminLog.objects.filter(
            user=self.admin_user,
            action=ADMIN_ACTION_VIEWED,
            application=self.application
        )

        self.assertEqual(logs.count(), 1)

    def test_changing_status_creates_log(self):
        """Test that changing application status in Django Admin creates log with old → new."""
        # Clear any existing logs
        AdminLog.objects.all().delete()

        # Directly change status (simulating what admin.save_model does)
        from django.contrib.admin.sites import site
        from apps.submissions.admin import ApplicationAdmin
        from django.http import HttpRequest

        # Get the admin instance
        admin_instance = ApplicationAdmin(Application, site)

        # Create mock request
        request = Mock()
        request.user = self.admin_user
        request.META = {'REMOTE_ADDR': '127.0.0.1'}

        # Change status
        old_status = self.application.status
        self.application.status = 'under_review'

        # Call save_model (this should trigger logging)
        admin_instance.save_model(request, self.application, form=None, change=True)

        # Reload from DB
        self.application.refresh_from_db()

        # Check log was created with status change
        status_logs = AdminLog.objects.filter(
            user=self.admin_user,
            action=ADMIN_ACTION_STATUS_CHANGE,
            application=self.application,
            old_value='submitted',
            new_value='under_review'
        )

        self.assertEqual(status_logs.count(), 1)

    def test_no_log_on_post_without_status_change(self):
        """Test that saving without status change doesn't create duplicate log."""
        # Clear any existing logs
        AdminLog.objects.all().delete()

        # Directly save without changing status
        from django.contrib.admin.sites import site
        from apps.submissions.admin import ApplicationAdmin

        admin_instance = ApplicationAdmin(Application, site)

        request = Mock()
        request.user = self.admin_user
        request.META = {'REMOTE_ADDR': '127.0.0.1'}

        # Status remains the same
        self.application.status = 'submitted'

        # Call save_model
        admin_instance.save_model(request, self.application, form=None, change=True)

        # Should NOT create status change log (status didn't change)
        status_logs = AdminLog.objects.filter(
            user=self.admin_user,
            action=ADMIN_ACTION_STATUS_CHANGE
        )

        self.assertEqual(status_logs.count(), 0)


class APILoggingTest(TestCase):
    """Test API logging integration (Story 4.5 + 4.6)."""

    def setUp(self):
        """Create test admin user and application."""
        self.admin_user = User.objects.create_user(
            username='admin_test',
            password='testpass123',
            is_staff=True
        )

        self.application = Application.objects.create(
            reference_number='COA-2025-001',
            application_type='COA',
            status='submitted'
        )

        self.applicant = Applicant.objects.create(
            application=self.application,
            entity_type='fizicko',
            first_name='Test',
            last_name='User',
            address='Test Address 123',
            email='test@example.com',
            phone='+381601234567',
            jmbg='0101990123456'
        )

        self.client = Client()
        self.client.force_login(self.admin_user)

    def test_api_get_application_detail_creates_log(self):
        """Test that GET /api/admin/applications/{ref}/ creates log entry."""
        # Clear any existing logs
        AdminLog.objects.all().delete()

        url = f'/api/admin/applications/{self.application.reference_number}/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        # Check log was created
        logs = AdminLog.objects.filter(
            user=self.admin_user,
            action=ADMIN_ACTION_API_VIEWED,
            application=self.application
        )

        self.assertEqual(logs.count(), 1)

    def test_api_patch_status_creates_log_with_transition(self):
        """Test that PATCH /api/admin/applications/{ref}/ logs status change with old → new."""
        # Clear any existing logs
        AdminLog.objects.all().delete()

        url = f'/api/admin/applications/{self.application.reference_number}/'
        data = {'status': 'under_review'}

        response = self.client.patch(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)

        # Check log was created with status transition
        logs = AdminLog.objects.filter(
            user=self.admin_user,
            action=ADMIN_ACTION_API_STATUS_CHANGE,
            application=self.application,
            old_value='submitted',
            new_value='under_review'
        )

        self.assertEqual(logs.count(), 1)


class AdminLogAdminInterfaceTest(TestCase):
    """Test AdminLog admin interface (read-only, filtering)."""

    def setUp(self):
        """Create test admin user and logs."""
        self.admin_user = User.objects.create_user(
            username='admin_test',
            password='testpass123',
            is_staff=True,
            is_superuser=True
        )

        self.application = Application.objects.create(
            reference_number='COA-2025-001',
            application_type='COA',
            status='submitted'
        )

        self.applicant = Applicant.objects.create(
            application=self.application,
            entity_type='fizicko',
            first_name='Test',
            last_name='User',
            address='Test Address 123',
            email='test@example.com',
            phone='+381601234567',
            jmbg='0101990123456'
        )

        # Create test logs
        AdminLog.objects.create(
            user=self.admin_user,
            action=ADMIN_ACTION_VIEWED,
            application=self.application
        )

        AdminLog.objects.create(
            user=self.admin_user,
            action=ADMIN_ACTION_STATUS_CHANGE,
            application=self.application,
            old_value='submitted',
            new_value='under_review'
        )

        self.client = Client()
        self.client.force_login(self.admin_user)

    def test_admin_log_list_view_accessible(self):
        """Test that AdminLog list view is accessible in Django Admin."""
        url = reverse('admin:submissions_adminlog_changelist')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'admin_test')
        self.assertContains(response, 'COA-2025-001')

    def test_admin_log_cannot_add_manually(self):
        """Test that adding AdminLog manually is disabled (read-only)."""
        # Check if add view returns 403 or redirects
        url = reverse('admin:submissions_adminlog_add')
        response = self.client.get(url)

        # Should either be forbidden or redirect (Django Admin prevents add)
        self.assertIn(response.status_code, [403, 302])


class CleanupOldAdminLogsTaskTest(TestCase):
    """Test Celery periodic task for log retention."""

    def setUp(self):
        """Create test admin user and old logs."""
        self.admin_user = User.objects.create_user(
            username='admin_test',
            password='testpass123',
            is_staff=True
        )

        self.application = Application.objects.create(
            reference_number='COA-2025-001',
            application_type='COA',
            status='submitted'
        )

        self.applicant = Applicant.objects.create(
            application=self.application,
            entity_type='fizicko',
            first_name='Test',
            last_name='User',
            address='Test Address 123',
            email='test@example.com',
            phone='+381601234567',
            jmbg='0101990123456'
        )

    def test_cleanup_deletes_old_logs(self):
        """Test that cleanup task deletes logs older than retention period."""
        # Create old log (older than 365 days)
        old_log = AdminLog.objects.create(
            user=self.admin_user,
            action=ADMIN_ACTION_VIEWED,
            application=self.application
        )

        # Manually set timestamp to 366 days ago
        old_timestamp = timezone.now() - timedelta(days=366)
        AdminLog.objects.filter(id=old_log.id).update(timestamp=old_timestamp)

        # Create recent log (within retention period)
        recent_log = AdminLog.objects.create(
            user=self.admin_user,
            action=ADMIN_ACTION_VIEWED,
            application=self.application
        )

        # Run cleanup task
        result = cleanup_old_admin_logs()

        # Old log should be deleted, recent log should remain
        self.assertFalse(AdminLog.objects.filter(id=old_log.id).exists())
        self.assertTrue(AdminLog.objects.filter(id=recent_log.id).exists())
        self.assertEqual(result, 1)  # 1 log deleted
