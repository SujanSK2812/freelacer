import logging
import sys
from django.core.mail import send_mail, get_connection
from django.conf import settings

logger = logging.getLogger(__name__)

def send_portal_email(subject, message, recipient_list, from_email=None, html_message=None):
    """
    Sends an email using standard Django send_mail.
    If SMTP fails (e.g., invalid Gmail App Password, network issue),
    it falls back to console backend and prints the email and links to the terminal.
    """
    from_email = from_email or getattr(settings, 'EMAIL_HOST_USER', 'noreply@freelancerportal.com')
    
    try:
        sent = send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=recipient_list,
            html_message=html_message,
            fail_silently=False,
        )
        print(f"\n[EMAIL SUCCESS] Sent email '{subject}' to {recipient_list} via SMTP.\n")
        return sent
    except Exception as e:
        print(f"\n==================================================================")
        print(f"[EMAIL NOTICE] SMTP delivery failed ({e}).")
        print(f"[EMAIL NOTICE] Falling back to console output so links are not lost:")
        print(f"TO: {recipient_list}")
        print(f"SUBJECT: {subject}")
        print(f"MESSAGE:\n{message}")
        print(f"==================================================================\n")
        
        try:
            console_conn = get_connection('django.core.mail.backends.console.EmailBackend')
            return send_mail(
                subject=subject,
                message=message,
                from_email=from_email,
                recipient_list=recipient_list,
                html_message=html_message,
                connection=console_conn,
                fail_silently=True
            )
        except Exception as fallback_err:
            logger.error(f"Console email fallback failed: {fallback_err}")
            return 0
