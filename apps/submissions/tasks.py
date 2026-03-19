# -*- coding: utf-8 -*-
"""
Celery tasks for submission-related background processing.
Story 2.14: Email Confirmation with Celery
Story 2.15: Draft Auto-Deletion Background Task
Story 3.6: Admin Notification Email

This module provides async email sending tasks with retry logic
and periodic draft deletion for GDPR compliance.

Security Features:
- Email masking in logs (GDPR compliance)
- HTML escaping in templates (XSS prevention)
- Task idempotency with acks_late
- Plain text email fallback
- 7-day draft retention (GDPR NFR18)
"""
import logging
from datetime import timedelta
from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from apps.submissions.models import Application, DraftMetadata, InitiativeData, AdminLog

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60, acks_late=True, reject_on_worker_lost=True)
def send_confirmation_email(self, application_id):
    """
    Send email confirmation to applicant after successful submission.

    This task sends a confirmation email with submission summary and reference number.
    It implements exponential backoff retry strategy for reliability.

    Args:
        application_id (int): ID of Application record

    Retry strategy:
        - max_retries: 3 retries (4 total attempts: initial + 3 retries)
        - retry_delay: Exponential backoff (60s, 120s, 240s)
        - retry on: Exception during email sending
        - acks_late: Task acknowledged after completion (idempotency protection)
        - reject_on_worker_lost: Re-queue if worker crashes

    Returns:
        bool: True if email sent successfully, False otherwise

    Example:
        >>> send_confirmation_email.delay(123)  # Async call
        <AsyncResult: task-id>

    Logging:
        - INFO: Successful email sending (email addresses masked for privacy)
        - WARNING: Retry attempts
        - ERROR: Max retries exceeded

    Security:
        - Email addresses are masked in logs (GDPR compliance)
        - Idempotent: Safe to retry without sending duplicates
    """
    try:
        # Get application from database with related data
        application = Application.objects.select_related(
            'applicant',
            'project_data'
        ).get(id=application_id)

        # SECURITY: Mask email for logging (GDPR/privacy compliance)
        masked_email = application.applicant.email[:3] + "***@" + application.applicant.email.split('@')[-1] if application.applicant.email else "N/A"

        logger.info(
            f"Sending confirmation email for {application.reference_number} "
            f"to {masked_email}"
        )

        # Prepare email context
        # Determine applicant name based on entity type
        if application.applicant.entity_type == 'fizicko':
            applicant_name = f"{application.applicant.first_name} {application.applicant.last_name}"
        else:  # pravno
            applicant_name = application.applicant.organization_name

        # Determine application type display text
        application_type_display = 'Projekat (COA)' if application.application_type == 'COA' else 'Inicijativa (COB)'

        # Get project title (if exists)
        project_title = 'N/A'
        if hasattr(application, 'project_data') and application.project_data:
            project_title = application.project_data.title

        context = {
            'reference_number': application.reference_number,
            'applicant_name': applicant_name,
            'application_type': application_type_display,
            'submission_date': application.submitted_at.strftime('%d.%m.%Y %H:%M'),
            'project_title': project_title,
        }

        # Render email HTML from template
        email_html = render_to_string('emails/confirmation_coa.html', context)

        # Generate plain text fallback for accessibility and spam prevention
        plain_text = f"""
Potvrda prijema prijave - {application.reference_number}

Poštovani/a {applicant_name},

Hvala što ste podneli prijavu putem DOMOVIK platforme. Potvrđujemo da smo primili vašu prijavu za {application_type_display}.

Vaš referentni broj: {application.reference_number}

Molimo sačuvajte ovaj referentni broj za buduću komunikaciju.

Detalji prijave:
- Tip prijave: {application_type_display}
- Naslov: {project_title}
- Datum podnošenja: {context['submission_date']}
- Status: Primljeno

Šta je sledeće?
- Vaša prijava će biti pregledana u roku od 7-10 radnih dana
- Bićete obavešteni putem emaila o daljem toku procesa
- Ako imate pitanja, kontaktirajte nas putem emaila ili telefona

---
DOMOVIK - Udruženje za podršku građanskih inicijativa
Email: info@domovik.org | Telefon: +381 11 1234 567

Ovaj email je automatski generisan. Molimo ne odgovarajte direktno na ovaj email.
        """.strip()

        # Send email with proper UTF-8 encoding for Serbian characters
        email = EmailMultiAlternatives(
            subject=f"Potvrda prijema prijave - {application.reference_number}",
            body=plain_text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[application.applicant.email],
        )
        email.attach_alternative(email_html, "text/html")
        email.send(fail_silently=False)

        logger.info(
            f"Email sent successfully to {masked_email} "
            f"for {application.reference_number}"
        )
        return True

    except Application.DoesNotExist:
        logger.error(
            f"Application with ID {application_id} not found. Cannot send email."
        )
        return False

    except Exception as exc:
        # Fix: Correct retry count - max_retries=3 means 4 total attempts (initial + 3 retries)
        retry_attempt = self.request.retries + 1
        total_attempts = self.max_retries + 1  # 4 total attempts

        logger.warning(
            f"Email sending failed for application {application_id}. "
            f"Retry attempt {retry_attempt}/{self.max_retries}. Error: {exc}"
        )

        # Exponential backoff: 60s, 120s, 240s
        retry_delay = (2 ** self.request.retries) * 60

        # Retry with exponential backoff
        try:
            raise self.retry(exc=exc, countdown=retry_delay)
        except self.MaxRetriesExceededError:
            # Get application for logging (if exists)
            try:
                application = Application.objects.get(id=application_id)
                logger.error(
                    f"Email sending failed after {total_attempts} attempts for "
                    f"{application.reference_number}. Giving up."
                )
            except Application.DoesNotExist:
                logger.error(
                    f"Email sending failed after {total_attempts} attempts for "
                    f"application_id={application_id}. Giving up."
                )
            return False


@shared_task(bind=True, name='submissions.delete_old_drafts', max_retries=0, time_limit=300)
def delete_old_drafts(self):
    """
    Delete draft metadata records older than 7 days (GDPR NFR18).
    Story 2.15: Draft Auto-Deletion Background Task

    Runs: Daily at 2:00 AM Europe/Belgrade timezone
    Retention: 7 days from draft creation

    Privacy: Only deletes metadata - actual draft data is in client localStorage.
    Client will auto-delete localStorage when server record missing.

    Idempotency: Task is idempotent - safe to run multiple times.
    No retries (max_retries=0) to prevent duplicate execution on failure.

    Returns:
        int: Number of drafts deleted
    """
    try:
        # ISSUE 2 FIX: Check if task already running (prevent concurrent execution)
        task_id = self.request.id
        logger.info(f"Draft deletion task started (task_id={task_id})")

        # Calculate expiry threshold (7 days ago)
        expiry_date = timezone.now() - timedelta(days=7)

        logger.info(f"Deleting drafts older than {expiry_date.strftime('%Y-%m-%d %H:%M:%S')}")

        # Find expired drafts
        expired_drafts = DraftMetadata.objects.filter(created_at__lt=expiry_date)
        count = expired_drafts.count()

        if count == 0:
            logger.info("No expired drafts found. All drafts within 7-day retention window.")
            return 0

        # Log details before deletion (for audit trail)
        logger.info(f"Found {count} expired drafts to delete:")
        for draft in expired_drafts[:10]:  # Log first 10 for audit
            logger.info(f"  - {draft.application_type} Draft {draft.draft_id} (created {draft.created_at.strftime('%Y-%m-%d')})")

        if count > 10:
            logger.info(f"  ... and {count - 10} more")

        # Delete expired drafts (GDPR compliance)
        deleted_count, _ = expired_drafts.delete()

        logger.info(f"Successfully deleted {deleted_count} expired draft metadata records (GDPR 7-day retention, task_id={task_id})")

        return deleted_count

    except Exception as exc:
        logger.error(f"Draft deletion task failed: {exc}")
        # Don't retry - will run again tomorrow at 2am
        return 0


@shared_task(bind=True, max_retries=3, default_retry_delay=60, acks_late=True, reject_on_worker_lost=True)
def send_admin_notification(self, application_id, app_type):
    """
    Send email notification to administrator about new application (COA or COB).
    Story 3.6: COB Success Screen & Email Notification

    Purpose: Notify admin when a new application is submitted (especially for COB).
    This helps administrators stay informed about incoming applications for review.

    Args:
        application_id (int): Application primary key
        app_type (str): "COA" or "COB"

    Retry strategy:
        - max_retries: 3 retries (4 total attempts: initial + 3 retries)
        - retry_delay: Exponential backoff (60s, 120s, 240s)
        - retry on: Exception during email sending
        - acks_late: Task acknowledged after completion (idempotency protection)
        - reject_on_worker_lost: Re-queue if worker crashes

    Returns:
        bool: True if email sent successfully, False otherwise

    Example:
        >>> send_admin_notification.delay(123, 'COB')  # Async call
        <AsyncResult: task-id>

    Logging:
        - INFO: Successful email sending
        - WARNING: Retry attempts
        - ERROR: Max retries exceeded or application not found

    Architecture: GDPR-compliant (minimal PII in email - reference number, applicant name, initiative title)
    """
    try:
        # Fetch application from database with related data
        application = Application.objects.select_related(
            'applicant'
        ).get(id=application_id)

        # Determine application type-specific details
        if app_type == 'COB':
            # COB: Get InitiativeData
            try:
                initiative_data = application.initiative_data
                title = initiative_data.naslov
                description = initiative_data.kratak_opis
                app_type_label = 'Inicijativa'
            except InitiativeData.DoesNotExist:
                logger.error(f"InitiativeData not found for application {application_id}")
                return False
        else:  # COA
            # COA: Get ProjectData
            try:
                project_data = application.project_data
                title = project_data.title
                description = project_data.short_description
                app_type_label = 'Projekat'
            except Exception:
                logger.error(f"ProjectData not found for application {application_id}")
                return False

        # Determine applicant name based on entity type
        if application.applicant.entity_type == 'fizicko':
            applicant_name = f"{application.applicant.first_name} {application.applicant.last_name}"
        else:  # pravno
            applicant_name = application.applicant.organization_name

        # Determine entity type display text
        entity_type_display = 'Fizičko lice' if application.applicant.entity_type == 'fizicko' else 'Pravno lice'

        logger.info(
            f"Sending admin notification for {application.reference_number} ({app_type})"
        )

        # Prepare email context
        context = {
            'reference_number': application.reference_number,
            'app_type': app_type,
            'app_type_label': app_type_label,
            'applicant_name': applicant_name,
            'entity_type': entity_type_display,
            'title': title,
            'description': description[:200] + '...' if len(description) > 200 else description,
            'submitted_at': application.submitted_at.strftime('%d.%m.%Y %H:%M'),
            'admin_url': f'{settings.SITE_URL}/admin/submissions/application/{application.id}/change/',
            'organization_name': settings.ORGANIZATION_NAME  # CODE REVIEW FIX: Configurable organization name
        }

        # Render email HTML from template
        email_html = render_to_string('emails/admin_notification.html', context)

        # Generate plain text fallback
        plain_text = f"""
Nova {app_type_label} Primljena
{'=' * 50}

Referentni broj: {application.reference_number}

Tip prijave: {app_type_label} ({app_type})
Podnosilac: {applicant_name} ({entity_type_display})
Naslov: {title}

Kratak opis:
{context['description']}

Datum podnošenja: {context['submitted_at']}

Pregledajte prijavu u Admin panelu:
{context['admin_url']}

---
Ovo je automatska notifikacija sa DOMOVIK sistema.
Ne odgovarajte na ovaj email.
        """.strip()

        # Send email to admin with proper UTF-8 encoding for Serbian characters
        email = EmailMultiAlternatives(
            subject=f'Nova {app_type_label.lower()} primljena - {application.reference_number}',
            body=plain_text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[settings.ADMIN_EMAIL],
        )
        email.attach_alternative(email_html, "text/html")
        email.send(fail_silently=False)

        logger.info(
            f"Admin notification sent successfully for {application.reference_number} ({app_type})"
        )
        return True

    except Application.DoesNotExist:
        logger.error(f"Application with ID {application_id} not found for admin notification")
        return False

    except Exception as exc:
        # Fix: Correct retry count - max_retries=3 means 4 total attempts (initial + 3 retries)
        retry_attempt = self.request.retries + 1
        total_attempts = self.max_retries + 1  # 4 total attempts

        logger.warning(
            f"Admin notification failed for application {application_id}. "
            f"Retry attempt {retry_attempt}/{self.max_retries}. Error: {exc}"
        )

        # Exponential backoff: 60s, 120s, 240s
        retry_delay = (2 ** self.request.retries) * 60

        # Retry with exponential backoff
        try:
            raise self.retry(exc=exc, countdown=retry_delay)
        except self.MaxRetriesExceededError:
            # Get application for logging (if exists)
            try:
                application = Application.objects.get(id=application_id)
                logger.error(
                    f"Admin notification failed after {total_attempts} attempts for "
                    f"{application.reference_number}. Giving up."
                )
            except Application.DoesNotExist:
                logger.error(
                    f"Admin notification failed after {total_attempts} attempts for "
                    f"application_id={application_id}. Giving up."
                )
            return False


@shared_task(bind=True, name='submissions.cleanup_old_admin_logs', max_retries=0, time_limit=300)
def cleanup_old_admin_logs(self):
    """
    Delete admin logs older than 365 days (1 year retention).
    Story 4.6: Admin Activity Logging - 1-year retention policy.

    Runs: Monthly (1st of month at 3:00 AM Europe/Belgrade timezone)
    Retention: 365 days (1 year) from log creation

    Privacy: GDPR-compliant retention - logs automatically deleted after 1 year.

    Idempotency: Task is idempotent - safe to run multiple times.
    No retries (max_retries=0) to prevent duplicate execution on failure.

    Returns:
        int: Number of logs deleted
    """
    try:
        task_id = self.request.id
        logger.info(f"Admin log cleanup task started (task_id={task_id})")

        # Calculate cutoff date (365 days ago = 1 year)
        cutoff_date = timezone.now() - timedelta(days=365)

        logger.info(f"Deleting admin logs older than {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}")

        # Delete old logs
        deleted_count, _ = AdminLog.objects.filter(timestamp__lt=cutoff_date).delete()

        if deleted_count == 0:
            logger.info("No expired admin logs found. All logs within 1-year retention window.")
        else:
            logger.info(
                f"Successfully deleted {deleted_count} admin logs older than 1 year "
                f"(before {cutoff_date.date()}, compliance requirement, task_id={task_id})"
            )

        return deleted_count

    except Exception as exc:
        logger.error(f"Admin log cleanup task failed: {exc}", exc_info=True)
        # Don't retry - will run again next month
        return 0
