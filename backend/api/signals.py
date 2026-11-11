from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail, mail_admins
from django.conf import settings
from django.contrib.auth import get_user_model

from .models import MassRequest


@receiver(post_save, sender=MassRequest)
def notify_admins_on_mass_request(sender, instance: MassRequest, created, **kwargs):
    if not created:
        return

    subject = f"Nouvelle demande de messe — {instance.preferred_date or 'date non précisée'}"
    requester = instance.requester
    who = f"{requester.first_name} {requester.last_name}" if requester else (instance.phone or 'Anonyme')
    message_lines = [
        f"Demandeur: {who}",
        f"Téléphone: {instance.phone}",
        f"Email: {instance.contact_email}",
        f"Date préférée: {instance.preferred_date}",
        "---",
        instance.message,
    ]
    message = "\n".join(filter(None, message_lines))

    # Try to send to staff users first
    User = get_user_model()
    staff_emails = list(User.objects.filter(is_staff=True, email__isnull=False).values_list('email', flat=True))

    try:
        if staff_emails:
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, staff_emails, fail_silently=True)
        else:
            # Fallback to mail_admins (requires ADMINS configured)
            mail_admins(subject, message, fail_silently=True)
    except Exception:
        # Don't raise on notification errors
        pass
