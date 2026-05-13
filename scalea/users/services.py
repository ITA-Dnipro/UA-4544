from django.conf import settings
from django.core.mail import send_mail

from .tokens import get_email_verification_token


def get_email_verification_link(user):
    token = get_email_verification_token(user)
    return f'{settings.FRONTEND_URL}/verify-email/{token}/'


def get_email_verification_content(user):
    link = get_email_verification_link(user)
    subject = 'Verify your email for Scalea'
    message = (
        'Hi there,\n\n'
        'Thank you for signing up for Scalea. Please confirm your email address to activate your account.\n'
        'Click the link below to verify your email:\n'
        f'{link}\n\n'
        'This link will expire in 24 hours. If you did not create an account, you can safely ignore this email.'
    )
    return {'subject': subject, 'message': message}


def send_email_verification(user):
    content = get_email_verification_content(user)
    send_mail(
        subject=content['subject'],
        message=content['message'],
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )
