from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from .models import Booking

@receiver(post_save, sender=Booking)
def send_ticket_email(sender, instance, created, **kwargs):
    # CHỈ CHẠY KHI: Không phải tạo mới (cập nhật) và status là 'paid'
    if not created and instance.payment_status == 'paid':
        subject = f"XÁC NHẬN VÉ ĐIỆN TỬ: {instance.booking_code}"
        
        # Truyền thông tin vào mẫu HTML email vé
        html_message = render_to_string('travel/e_ticket.html', {'booking': instance})
        plain_message = strip_tags(html_message)
        
        msg = EmailMultiAlternatives(
            subject, plain_message, settings.EMAIL_HOST_USER, [instance.email]
        )
        msg.attach_alternative(html_message, "text/html")
        msg.send()