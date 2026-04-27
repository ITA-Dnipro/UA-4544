from django.contrib.auth.tokens import PasswordResetTokenGenerator


class CustomPasswordResetTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{user.password}{user.is_active}{timestamp}"


password_reset_token = CustomPasswordResetTokenGenerator()
