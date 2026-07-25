# -*- coding: utf-8 -*-
"""
Tests for purge_orphan_uploads() - Z8 (2026-07-25).

Covers the GDPR retention promise for documents attached to an application that was
never submitted: they must disappear after DRAFT_RETENTION_DAYS, while documents of a
real submission must survive untouched.
"""
import shutil
import tempfile
from datetime import timedelta
from pathlib import Path

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.submissions.constants import ApplicationType, DRAFT_RETENTION_DAYS
from apps.submissions.models import Application, FileMetadata, UploadedFile
from apps.submissions.tasks import purge_orphan_uploads


class PurgeOrphanUploadsTests(TestCase):
    """purge_orphan_uploads() deletes abandoned uploads and nothing else."""

    def setUp(self):
        self.media_root = tempfile.mkdtemp(prefix='domovik-test-media-')
        self.addCleanup(shutil.rmtree, self.media_root, True)

        self.override = override_settings(MEDIA_ROOT=self.media_root)
        self.override.enable()
        self.addCleanup(self.override.disable)

        self.uploads = Path(self.media_root) / 'uploads' / 'drafts'
        self.uploads.mkdir(parents=True)

        self.old = timezone.now() - timedelta(days=DRAFT_RETENTION_DAYS + 1)
        self.recent = timezone.now() - timedelta(days=1)

    # --- helpers ---------------------------------------------------------
    def _make_upload(self, name, uploaded_at, application=None):
        """Create an UploadedFile row plus its file on disk."""
        path = self.uploads / name
        path.write_bytes(b'x' * 10)

        record = UploadedFile.objects.create(
            original_filename=name,
            stored_filename=name,
            file_path=f'uploads/drafts/{name}',
            file_size=10,
            file_type='pdf',
            mime_type='application/pdf',
            category='BUDGET',
            uploaded_by_session='session-key',
            application=application,
        )
        # upload_date is auto_now_add, so it has to be backdated after the insert.
        UploadedFile.objects.filter(pk=record.pk).update(upload_date=uploaded_at)
        return record, path

    def _make_stray(self, name, mtime):
        """Create a file on disk with no matching database row."""
        path = self.uploads / name
        path.write_bytes(b'x' * 10)
        stamp = mtime.timestamp()
        import os
        os.utime(path, (stamp, stamp))
        return path

    # --- orphan rows -----------------------------------------------------
    def test_deletes_expired_orphan_row_and_its_file(self):
        record, path = self._make_upload('old_orphan.pdf', self.old)

        rows, strays = purge_orphan_uploads()

        self.assertEqual((rows, strays), (1, 0))
        self.assertFalse(UploadedFile.objects.filter(pk=record.pk).exists())
        self.assertFalse(path.exists())

    def test_keeps_orphan_row_inside_retention_window(self):
        record, path = self._make_upload('fresh_orphan.pdf', self.recent)

        rows, strays = purge_orphan_uploads()

        self.assertEqual((rows, strays), (0, 0))
        self.assertTrue(UploadedFile.objects.filter(pk=record.pk).exists())
        self.assertTrue(path.exists())

    def test_keeps_files_of_a_submitted_application_however_old(self):
        application = Application.objects.create(
            reference_number='COA-2026-001',
            application_type=ApplicationType.COA,
        )
        record, path = self._make_upload('submitted.pdf', self.old, application=application)

        rows, strays = purge_orphan_uploads()

        self.assertEqual((rows, strays), (0, 0))
        self.assertTrue(UploadedFile.objects.filter(pk=record.pk).exists())
        self.assertTrue(path.exists())

    # --- stray files -----------------------------------------------------
    def test_deletes_expired_stray_file(self):
        path = self._make_stray('untracked.pdf', self.old)

        rows, strays = purge_orphan_uploads()

        self.assertEqual((rows, strays), (0, 1))
        self.assertFalse(path.exists())

    def test_keeps_stray_file_inside_retention_window(self):
        path = self._make_stray('untracked_fresh.pdf', self.recent)

        rows, strays = purge_orphan_uploads()

        self.assertEqual((rows, strays), (0, 0))
        self.assertTrue(path.exists())

    def test_never_deletes_a_referenced_file_even_when_old_on_disk(self):
        """An old file on disk is safe as long as some row still points at it."""
        import os

        application = Application.objects.create(
            reference_number='COA-2026-002',
            application_type=ApplicationType.COA,
        )
        _, path = self._make_upload('referenced.pdf', self.recent, application=application)
        stamp = self.old.timestamp()
        os.utime(path, (stamp, stamp))

        rows, strays = purge_orphan_uploads()

        self.assertEqual((rows, strays), (0, 0))
        self.assertTrue(path.exists())

    # --- FileMetadata protection -----------------------------------------
    # services.resolve_file_on_disk() can find a file from FileMetadata alone, so a
    # name claimed there must survive even when the UploadedFile side looks abandoned.
    def _claim_in_file_metadata(self, name):
        application = Application.objects.create(
            reference_number=f'COA-2026-{FileMetadata.objects.count() + 100}',
            application_type=ApplicationType.COA,
        )
        FileMetadata.objects.create(
            application=application,
            file_type='BUDGET',
            original_filename=name,
            stored_filename=name,
            file_size=10,
        )

    def test_keeps_orphan_row_when_file_metadata_claims_the_name(self):
        record, path = self._make_upload('claimed.pdf', self.old)
        self._claim_in_file_metadata('claimed.pdf')

        rows, strays = purge_orphan_uploads()

        self.assertEqual((rows, strays), (0, 0))
        self.assertTrue(UploadedFile.objects.filter(pk=record.pk).exists())
        self.assertTrue(path.exists())

    def test_keeps_stray_file_when_file_metadata_claims_the_name(self):
        path = self._make_stray('claimed_stray.pdf', self.old)
        self._claim_in_file_metadata('claimed_stray.pdf')

        rows, strays = purge_orphan_uploads()

        self.assertEqual((rows, strays), (0, 0))
        self.assertTrue(path.exists())

    # --- dry run ---------------------------------------------------------
    def test_dry_run_reports_but_deletes_nothing(self):
        record, record_path = self._make_upload('old_orphan.pdf', self.old)
        stray_path = self._make_stray('untracked.pdf', self.old)

        rows, strays = purge_orphan_uploads(dry_run=True)

        self.assertEqual((rows, strays), (1, 1))
        self.assertTrue(UploadedFile.objects.filter(pk=record.pk).exists())
        self.assertTrue(record_path.exists())
        self.assertTrue(stray_path.exists())

    def test_is_idempotent(self):
        self._make_upload('old_orphan.pdf', self.old)
        self._make_stray('untracked.pdf', self.old)

        self.assertEqual(purge_orphan_uploads(), (1, 1))
        self.assertEqual(purge_orphan_uploads(), (0, 0))
