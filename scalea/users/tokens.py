from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core import signing


password_reset_token = PasswordResetTokenGenerator()


def get_email_verification_token(user):
    payload = {
        'user_id': user.pk,
        'email': user.email,
    }
    return signing.dumps(payload, salt=settings.EMAIL_VERIFICATION_SALT)


def decode_email_verification_token(token, max_age=settings.EMAIL_VERIFICATION_MAX_AGE):
    try:
        return signing.loads(
            token,
            salt=settings.EMAIL_VERIFICATION_SALT,
            max_age=max_age,
        )
    except signing.BadSignature:
        return None
