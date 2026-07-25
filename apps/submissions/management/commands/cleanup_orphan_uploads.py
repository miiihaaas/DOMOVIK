# -*- coding: utf-8 -*-
"""
Management command: delete uploaded files that never reached a submitted application.

Z8 (2026-07-25): purge_expired_drafts() only removed DraftMetadata rows, so documents
attached to an abandoned form stayed on disk indefinitely (files from March 2026 were
still present in July). Those are personal data - CVs, budgets, letters of support -
kept well past the 7-day draft retention the privacy policy promises.

Run from cron, e.g. daily at 02:30 Europe/Belgrade (after delete_old_drafts):

    30 2 * * * cd /var/www/domovik && venv/bin/python manage.py cleanup_orphan_uploads >> logs/maintenance.log 2>&1
"""
from django.core.management.base import BaseCommand

from apps.submissions.constants import DRAFT_RETENTION_DAYS
from apps.submissions.tasks import purge_orphan_uploads


class Command(BaseCommand):
    help = (
        f"Delete uploaded files not linked to any application and older than "
        f"{DRAFT_RETENTION_DAYS} days (GDPR retention)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help="Only report what would be deleted, without deleting anything.",
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        rows, strays = purge_orphan_uploads(dry_run=dry_run)

        summary = f"{rows} orphan upload record(s) and {strays} stray file(s)"
        if dry_run:
            self.stdout.write(f"[dry-run] Would delete {summary}.")
        else:
            self.stdout.write(self.style.SUCCESS(f"Deleted {summary}."))
