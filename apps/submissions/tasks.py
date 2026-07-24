# -*- coding: utf-8 -*-
"""
Email + maintenance logic for submissions.
Story 2.14: Email Confirmation
Story 2.15: Draft Auto-Deletion
Story 3.6: Admin Notification Email
Z4′ (2026-07-24): Email sending moved to a SYNCHRONOUS request-path by default.

Why Z4′:
    Production has no running Celery worker (worker died 2026-06-03, MySQL broker
    silently queued tasks that were never consumed). SMTP itself is healthy.
    So email is now delivered in-request via *_now() helpers, and periodic jobs run
    from cron via management commands (see apps/submissions/management/commands/).
    The Celery @shared_task wrappers are kept intact so the async path still works
    if a worker is ever brought back.

Structure:
    _deliver_*   -> plain function with the actual work; raises on failure.
    send_*       -> Celery task wrapper (retry semantics); unchanged behaviour.
    *_now        -> synchronous wrapper for the request path; never raises.
    purge_*      -> plain maintenance functions used by tasks AND cron commands.

Security Features:
- Email masking in logs (GDPR compliance)
- HTML escaping in templates (XSS prevention)
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


# ============================================================================
# Applicant confirmation email
# ============================================================================

def _deliver_confirmation_email(application_id):
    """
    Build and send the applicant confirmation email.

    Returns:
        bool: True on success.

    Raises:
        Application.DoesNotExist: if the application is missing.
        Exception: on any email build/send failure (caller decides retry vs log).
    """
    application = Application.objects.select_related(
        'applicant',
        'project_data'
    ).get(id=application_id)

    # SECURITY: Mask email for logging (GDPR/privacy compliance)
    masked_email = (
        application.applicant.email[:3] + "***@" + application.applicant.email.split('@')[-1]
        if application.applicant.email else "N/A"
    )

    logger.info(
        f"Sending confirmation email for {application.reference_number} to {masked_email}"
    )

    # Determine applicant name based on entity type
    if application.applicant.entity_type == 'fizicko':
        applicant_name = f"{application.applicant.first_name} {application.applicant.last_name}"
    else:  # pravno
        applicant_name = application.applicant.organization_name

    application_type_display = (
        'Projekat (COA)' if application.application_type == 'COA' else 'Inicijativa (COB)'
    )

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

    email_html = render_to_string('emails/confirmation_coa.html', context)

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

    email = EmailMultiAlternatives(
        subject=f"Potvrda prijema prijave - {application.reference_number}",
        body=plain_text,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[application.applicant.email],
    )
    email.attach_alternative(email_html, "text/html")
    email.send(fail_silently=False)

    logger.info(
        f"Email sent successfully to {masked_email} for {application.reference_number}"
    )
    return True


def send_confirmation_email_now(application_id):
    """
    Z4′: Synchronous confirmation email used from the request path.

    Never raises - a failed email must NOT break a successful submission.
    The applicant always has the reference number + downloadable PDF regardless.

    Returns:
        bool: True if sent, False otherwise.
    """
    try:
        return _deliver_confirmation_email(application_id)
    except Application.DoesNotExist:
        logger.error(f"Application {application_id} not found; confirmation email skipped.")
        return False
    except Exception as exc:
        logger.error(
            f"Confirmation email failed for application {application_id}: {exc}",
            exc_info=True
        )
        return False


@shared_task(bind=True, max_retries=3, default_retry_delay=60, acks_late=True, reject_on_worker_lost=True)
def send_confirmation_email(self, application_id):
    """
    Celery task wrapper for applicant confirmation email (async path).

    Kept for backwards compatibility / future worker use. Production currently
    delivers via send_confirmation_email_now() instead (Z4′).

    Retry strategy: max_retries=3 (4 total attempts), exponential backoff 60/120/240s.
    """
    try:
        return _deliver_confirmation_email(application_id)
    except Application.DoesNotExist:
        logger.error(f"Application with ID {application_id} not found. Cannot send email.")
        return False
    except Exception as exc:
        retry_attempt = self.request.retries + 1
        total_attempts = self.max_retries + 1

        logger.warning(
            f"Email sending failed for application {application_id}. "
            f"Retry attempt {retry_attempt}/{self.max_retries}. Error: {exc}"
        )

        retry_delay = (2 ** self.request.retries) * 60

        try:
            raise self.retry(exc=exc, countdown=retry_delay)
        except self.MaxRetriesExceededError:
            logger.error(
                f"Email sending failed after {total_attempts} attempts for "
                f"application_id={application_id}. Giving up."
            )
            return False


# ============================================================================
# Admin notification email
# ============================================================================

def _deliver_admin_notification(application_id, app_type):
    """
    Build and send the admin notification email about a new application.

    Returns:
        bool: True on success (False if related data missing).

    Raises:
        Application.DoesNotExist: if the application is missing.
        Exception: on any email build/send failure.
    """
    application = Application.objects.select_related('applicant').get(id=application_id)

    if app_type == 'COB':
        try:
            initiative_data = application.initiative_data
            title = initiative_data.naslov
            description = initiative_data.kratak_opis
            app_type_label = 'Inicijativa'
        except InitiativeData.DoesNotExist:
            logger.error(f"InitiativeData not found for application {application_id}")
            return False
    else:  # COA
        try:
            project_data = application.project_data
            title = project_data.title
            description = project_data.short_description
            app_type_label = 'Projekat'
        except Exception:
            logger.error(f"ProjectData not found for application {application_id}")
            return False

    if application.applicant.entity_type == 'fizicko':
        applicant_name = f"{application.applicant.first_name} {application.applicant.last_name}"
    else:  # pravno
        applicant_name = application.applicant.organization_name

    entity_type_display = (
        'Fizičko lice' if application.applicant.entity_type == 'fizicko' else 'Pravno lice'
    )

    logger.info(
        f"Sending admin notification for {application.reference_number} ({app_type})"
    )

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
        'organization_name': settings.ORGANIZATION_NAME
    }

    email_html = render_to_string('emails/admin_notification.html', context)

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


def send_admin_notification_now(application_id, app_type):
    """
    Z4′: Synchronous admin notification used from the request path. Never raises.

    Returns:
        bool: True if sent, False otherwise.
    """
    try:
        return _deliver_admin_notification(application_id, app_type)
    except Application.DoesNotExist:
        logger.error(f"Application {application_id} not found; admin notification skipped.")
        return False
    except Exception as exc:
        logger.error(
            f"Admin notification failed for application {application_id}: {exc}",
            exc_info=True
        )
        return False


@shared_task(bind=True, max_retries=3, default_retry_delay=60, acks_late=True, reject_on_worker_lost=True)
def send_admin_notification(self, application_id, app_type):
    """
    Celery task wrapper for admin notification (async path).

    Kept for backwards compatibility / future worker use. Production currently
    delivers via send_admin_notification_now() instead (Z4′).
    """
    try:
        return _deliver_admin_notification(application_id, app_type)
    except Application.DoesNotExist:
        logger.error(f"Application with ID {application_id} not found for admin notification")
        return False
    except Exception as exc:
        retry_attempt = self.request.retries + 1
        total_attempts = self.max_retries + 1

        logger.warning(
            f"Admin notification failed for application {application_id}. "
            f"Retry attempt {retry_attempt}/{self.max_retries}. Error: {exc}"
        )

        retry_delay = (2 ** self.request.retries) * 60

        try:
            raise self.retry(exc=exc, countdown=retry_delay)
        except self.MaxRetriesExceededError:
            logger.error(
                f"Admin notification failed after {total_attempts} attempts for "
                f"application_id={application_id}. Giving up."
            )
            return False


# ============================================================================
# Maintenance jobs (draft cleanup + admin log cleanup)
# Z4′: run from cron via management commands; Celery tasks kept as wrappers.
# ============================================================================

def purge_expired_drafts():
    """
    Delete DraftMetadata records older than 7 days (GDPR NFR18).

    Privacy: only metadata is deleted - actual draft data lives in client localStorage.
    Idempotent.

    Returns:
        int: number of drafts deleted.
    """
    expiry_date = timezone.now() - timedelta(days=7)
    logger.info(f"Deleting drafts older than {expiry_date.strftime('%Y-%m-%d %H:%M:%S')}")

    expired_drafts = DraftMetadata.objects.filter(created_at__lt=expiry_date)
    count = expired_drafts.count()

    if count == 0:
        logger.info("No expired drafts found. All drafts within 7-day retention window.")
        return 0

    logger.info(f"Found {count} expired drafts to delete:")
    for draft in expired_drafts[:10]:
        logger.info(
            f"  - {draft.application_type} Draft {draft.draft_id} "
            f"(created {draft.created_at.strftime('%Y-%m-%d')})"
        )
    if count > 10:
        logger.info(f"  ... and {count - 10} more")

    deleted_count, _ = expired_drafts.delete()
    logger.info(
        f"Successfully deleted {deleted_count} expired draft metadata records "
        f"(GDPR 7-day retention)"
    )
    return deleted_count


def purge_old_admin_logs():
    """
    Delete AdminLog records older than 365 days (1-year retention).
    Idempotent.

    Returns:
        int: number of logs deleted.
    """
    cutoff_date = timezone.now() - timedelta(days=365)
    logger.info(f"Deleting admin logs older than {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}")

    deleted_count, _ = AdminLog.objects.filter(timestamp__lt=cutoff_date).delete()

    if deleted_count == 0:
        logger.info("No expired admin logs found. All logs within 1-year retention window.")
    else:
        logger.info(
            f"Successfully deleted {deleted_count} admin logs older than 1 year "
            f"(before {cutoff_date.date()})"
        )
    return deleted_count


@shared_task(bind=True, name='submissions.delete_old_drafts', max_retries=0, time_limit=300)
def delete_old_drafts(self):
    """Celery wrapper around purge_expired_drafts() (async path). No retries."""
    try:
        logger.info(f"Draft deletion task started (task_id={self.request.id})")
        return purge_expired_drafts()
    except Exception as exc:
        logger.error(f"Draft deletion task failed: {exc}")
        return 0


@shared_task(bind=True, name='submissions.cleanup_old_admin_logs', max_retries=0, time_limit=300)
def cleanup_old_admin_logs(self):
    """Celery wrapper around purge_old_admin_logs() (async path). No retries."""
    try:
        logger.info(f"Admin log cleanup task started (task_id={self.request.id})")
        return purge_old_admin_logs()
    except Exception as exc:
        logger.error(f"Admin log cleanup task failed: {exc}", exc_info=True)
        return 0
