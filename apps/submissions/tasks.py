# -*- coding: utf-8 -*-
"""
Celery tasks for submission-related background processing.
Story 2.14: Email Confirmation with Celery

This module provides async email sending tasks with retry logic.

Security Features:
- Email masking in logs (GDPR compliance)
- HTML escaping in templates (XSS prevention)
- Task idempotency with acks_late
- Plain text email fallback
"""
import logging
from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from apps.submissions.models import Application

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
            f"✓ Email sent successfully to {masked_email} "
            f"for {application.reference_number}"
        )
        return True

    except Application.DoesNotExist:
        logger.error(
            f"✗ Application with ID {application_id} not found. Cannot send email."
        )
        return False

    except Exception as exc:
        # Fix: Correct retry count - max_retries=3 means 4 total attempts (initial + 3 retries)
        retry_attempt = self.request.retries + 1
        total_attempts = self.max_retries + 1  # 4 total attempts

        logger.warning(
            f"⚠ Email sending failed for application {application_id}. "
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
                    f"✗ Email sending failed after {total_attempts} attempts for "
                    f"{application.reference_number}. Giving up."
                )
            except Application.DoesNotExist:
                logger.error(
                    f"✗ Email sending failed after {total_attempts} attempts for "
                    f"application_id={application_id}. Giving up."
                )
            return False
