# -*- coding: utf-8 -*-
"""
Management command: repair FileMetadata.stored_filename for records whose file
cannot be located on disk (the COB download-404 bug, Z1 2026-07-24).

Root cause: submit_cob used to trust the browser-sent filename, so FileMetadata.stored_filename
held the ORIGINAL name instead of the timestamped name actually on disk. Downloads 404'd.
submit_cob is now fixed; this command repairs the already-broken rows.

Safety rules (deliberately conservative — never guess):
  - Only touches FileMetadata whose file is currently NOT found on disk.
  - Finds the matching UploadedFile by (application, category) whose stored file DOES exist.
  - Prefers an exact original_filename match; requires an UNAMBIGUOUS candidate.
  - Skips (and reports) anything ambiguous or unresolvable — a human decides those.

Usage:
    python manage.py fix_file_metadata --dry-run      # report only, change nothing
    python manage.py fix_file_metadata                # apply repairs
"""
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.submissions.models import FileMetadata, UploadedFile
from apps.submissions.services import resolve_file_on_disk


class Command(BaseCommand):
    help = "Repair FileMetadata.stored_filename for records whose file is missing on disk."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help="Report planned changes without modifying the database.",
        )

    def _uploadedfile_exists_on_disk(self, uf):
        """True if the UploadedFile's stored file is present on disk."""
        if uf.file_path:
            try:
                if os.path.exists(uf.file_path.path):
                    return True
            except (ValueError, NotImplementedError):
                pass
        drafts_path = os.path.join(
            settings.MEDIA_ROOT, 'uploads', 'drafts', uf.stored_filename
        )
        return os.path.exists(drafts_path)

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        total = FileMetadata.objects.count()
        ok = fixed = skipped_ok = skipped_unresolved = skipped_ambiguous = 0

        self.stdout.write(f"Scanning {total} FileMetadata record(s)...")

        for fm in FileMetadata.objects.select_related('application').order_by('application_id', 'id'):
            ref = fm.application.reference_number

            # Already resolvable? Leave it alone.
            if resolve_file_on_disk(fm) is not None:
                skipped_ok += 1
                continue

            # Broken: find candidate UploadedFile records for this application + category.
            candidates = list(UploadedFile.objects.filter(
                application_id=fm.application_id,
                category=fm.file_type,
                is_deleted=False,
            ))
            # Only those whose file is actually on disk are usable.
            usable = [uf for uf in candidates if self._uploadedfile_exists_on_disk(uf)]

            # Prefer an exact original_filename match when it narrows things down.
            exact = [uf for uf in usable if uf.original_filename == fm.original_filename]
            chosen_pool = exact if exact else usable

            # Deduplicate by stored_filename to detect real ambiguity.
            distinct = {uf.stored_filename for uf in chosen_pool}

            if len(distinct) == 0:
                skipped_unresolved += 1
                self.stdout.write(self.style.WARNING(
                    f"  [SKIP no-disk-match] {ref} {fm.file_type} "
                    f"orig={fm.original_filename!r} cur={fm.stored_filename!r}"
                ))
                continue

            if len(distinct) > 1:
                skipped_ambiguous += 1
                self.stdout.write(self.style.WARNING(
                    f"  [SKIP ambiguous] {ref} {fm.file_type} orig={fm.original_filename!r} "
                    f"candidates={sorted(distinct)}"
                ))
                continue

            new_stored = distinct.pop()
            fixed += 1
            self.stdout.write(self.style.SUCCESS(
                f"  [{'DRY' if dry_run else 'FIX'}] {ref} {fm.file_type} "
                f"{fm.stored_filename!r} -> {new_stored!r}"
            ))
            if not dry_run:
                fm.stored_filename = new_stored
                fm.save(update_fields=['stored_filename'])

        ok = skipped_ok
        self.stdout.write("")
        self.stdout.write(
            f"Done. resolvable-already={ok}, "
            f"{'would-fix' if dry_run else 'fixed'}={fixed}, "
            f"skipped(no-disk-match)={skipped_unresolved}, "
            f"skipped(ambiguous)={skipped_ambiguous}"
        )
        if dry_run and fixed:
            self.stdout.write(self.style.NOTICE("Dry-run only — re-run without --dry-run to apply."))
