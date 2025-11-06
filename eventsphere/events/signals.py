from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.core.mail import send_mail
from .models import Event

@receiver(pre_save, sender=Event)
def notify_organizer_on_status_change(sender, instance, **kwargs):
    if not instance.pk:
        # It's a new event, skip notification
        return
    
    try:
        previous = Event.objects.get(pk=instance.pk)
    except Event.DoesNotExist:
        return

    if previous.approval_status != instance.approval_status:
        subject = ""
        message = ""

        if instance.approval_status == Event.STATUS_APPROVED:
            subject = f"Your event '{instance.title}' has been approved!"
            message = (
                f"Congratulations! Your event '{instance.title}' has been approved "
                f"and is now visible on EventSphere.\n\n"
                f"Event details:\nTitle: {instance.title}\nDate: {instance.date}\nLocation: {instance.location}\n"
            )
        elif instance.approval_status == Event.STATUS_REJECTED:
            subject = f"Your event '{instance.title}' has been rejected"
            message = (
                f"Unfortunately, your event '{instance.title}' has been rejected.\n"
                f"If you’d like more information, please contact the admin team.\n"
            )
        else:
            return  # No email for pending state

        send_mail(
            subject,
            message,
            "noreply@eventsphere.com",
            [instance.organizer.email],
            fail_silently=True,
        )
