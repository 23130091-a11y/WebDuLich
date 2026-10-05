import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from .models import Booking

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Booking)
def _stash_old_payment_status(sender, instance, **kwargs):
    # Giữ status cũ để post_save biết đây có phải lần chuyển sang 'paid' không
    if instance.pk:
        try:
            instance._old_payment_status = Booking.objects.values_list(
                'payment_status', flat=True).get(pk=instance.pk)
        except Booking.DoesNotExist:
            instance._old_payment_status = None
    else:
        instance._old_payment_status = None


@receiver(post_save, sender=Booking)
def send_ticket_email(sender, instance, created, **kwargs):
    # CHỈ CHẠY 1 LẦN: khi payment_status vừa chuyển sang 'paid'.
    # (bản cũ gửi lại mỗi lần .save() + SMTP chết làm fail cả transaction)
    if created or getattr(instance, '_old_payment_status', None) == 'paid':
        return
    if instance.payment_status != 'paid':
        return
    try:
        subject = f"XÁC NHẬN VÉ ĐIỆN TỬ: {instance.booking_code}"
        html_message = render_to_string('travel/e_ticket.html', {'booking': instance})
        plain_message = strip_tags(html_message)
        msg = EmailMultiAlternatives(
            subject, plain_message, settings.EMAIL_HOST_USER, [instance.email]
        )
        msg.attach_alternative(html_message, "text/html")
        msg.send()
    except Exception:
        logger.exception("Gửi email vé thất bại cho booking %s", instance.pk)
