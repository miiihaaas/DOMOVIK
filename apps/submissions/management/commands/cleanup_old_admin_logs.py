# -*- coding: utf-8 -*-
"""
Management command: delete AdminLog older than 365 days (1-year retention).

Z4' (2026-07-24): replaces the Celery periodic task on production (no worker running).
Run from cron, e.g. monthly on the 1st at 03:00:

    0 3 1 * * cd /var/www/domovik && venv/bin/python manage.py cleanup_old_admin_logs >> logs/maintenance.log 2>&1
"""
from django.core.management.base import BaseCommand

from apps.submissions.tasks import purge_old_admin_logs


class Command(BaseCommand):
    help = "Delete admin activity logs older than 365 days (1-year retention)."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help="Only report how many logs would be deleted, without deleting.",
        )

    def handle(self, *args, **options):
        if options['dry_run']:
            from datetime import timedelta
            from django.utils import timezone
            from apps.submissions.models import AdminLog

            cutoff_date = timezone.now() - timedelta(days=365)
            count = AdminLog.objects.filter(timestamp__lt=cutoff_date).count()
            self.stdout.write(f"[dry-run] {count} admin log(s) older than 1 year would be deleted.")
            return

        deleted = purge_old_admin_logs()
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted} old admin log(s)."))
