import hashlib
from django.contrib.auth.tokens import PasswordResetTokenGenerator

password_reset_token = PasswordResetTokenGenerator()


def hash_token(token):
    """Hash token for storage in database (single-use tracking)."""
    return hashlib.sha256(token.encode()).hexdigest()

