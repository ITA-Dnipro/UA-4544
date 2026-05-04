from rest_framework.throttling import AnonRateThrottle


class ResendVerificationEmailThrottle(AnonRateThrottle):
    scope = 'resend_verification_email'
