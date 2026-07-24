# -*- coding: utf-8 -*-
"""
Management command: delete DraftMetadata older than 7 days (GDPR NFR18).

Z4' (2026-07-24): replaces the Celery periodic task on production (no worker running).
Run from cron, e.g. daily at 02:00 Europe/Belgrade:

    0 2 * * * cd /var/www/domovik && venv/bin/python manage.py delete_old_drafts >> logs/maintenance.log 2>&1
"""
from django.core.management.base import BaseCommand

from apps.submissions.tasks import purge_expired_drafts


class Command(BaseCommand):
    help = "Delete draft metadata older than 7 days (GDPR 7-day retention)."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help="Only report how many drafts would be deleted, without deleting.",
        )

    def handle(self, *args, **options):
        if options['dry_run']:
            from datetime import timedelta
            from django.utils import timezone
            from apps.submissions.models import DraftMetadata

            expiry_date = timezone.now() - timedelta(days=7)
            count = DraftMetadata.objects.filter(created_at__lt=expiry_date).count()
            self.stdout.write(f"[dry-run] {count} draft(s) older than 7 days would be deleted.")
            return

        deleted = purge_expired_drafts()
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted} expired draft(s)."))
