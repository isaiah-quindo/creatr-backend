"""
Email sending for account verification.

If RESEND_API_KEY is set, we send via the Resend HTTP API (production).
Otherwise we fall through to Django's configured EMAIL_BACKEND, which in dev
points at Mailtrap's sandbox SMTP.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


def _build_verification_link(token: str) -> str:
    return f"{settings.FRONTEND_URL}/verify-email/confirm?token={token}"


def send_verification_email(user, token: str) -> None:
    """Send the verification email. Failures are logged, not raised — we don't
    want a transient mail outage to prevent account creation."""

    link = _build_verification_link(token)
    context = {
        "link": link,
        "user": user,
        "expires_hours": settings.EMAIL_VERIFICATION_TOKEN_HOURS,
    }

    subject = "Verify your Creatr email"
    html_body = render_to_string("accounts/email/verification.html", context)
    text_body = render_to_string("accounts/email/verification.txt", context).strip()

    try:
        if settings.RESEND_API_KEY:
            _send_via_resend(
                to=user.email,
                subject=subject,
                html=html_body,
                text=text_body,
            )
        else:
            _send_via_django(
                to=user.email,
                subject=subject,
                html=html_body,
                text=text_body,
            )
    except Exception:
        logger.exception("Failed to send verification email to %s", user.email)


def _send_via_django(*, to: str, subject: str, html: str, text: str) -> None:
    msg = EmailMultiAlternatives(
        subject=subject,
        body=text or strip_tags(html),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to],
    )
    msg.attach_alternative(html, "text/html")
    msg.send(fail_silently=False)


def _send_via_resend(*, to: str, subject: str, html: str, text: str) -> None:
    # Imported lazily so the dependency is optional in dev.
    import resend  # type: ignore[import-not-found]

    resend.api_key = settings.RESEND_API_KEY
    resend.Emails.send({
        "from": settings.DEFAULT_FROM_EMAIL,
        "to": [to],
        "subject": subject,
        "html": html,
        "text": text,
    })
