import hashlib

from django.core.cache import cache

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_SECONDS = 15 * 60


def _normalize_email(email: str) -> str:
    return hashlib.sha256(email.strip().lower().encode('utf-8')).hexdigest()


def _fail_key(email: str) -> str:
    return f'auth:login:count:{_normalize_email(email)}'


def _lock_key(email: str) -> str:
    return f'auth:login:lock:{_normalize_email(email)}'


def is_locked(email: str) -> bool:
    return bool(cache.get(_lock_key(email)))


def register_failure(email: str) -> None:
    key = _fail_key(email)
    try:
        count = cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=LOCKOUT_SECONDS)
        count = 1

    if count >= MAX_FAILED_ATTEMPTS:
        cache.set(_lock_key(email), True, timeout=LOCKOUT_SECONDS)


def clear_failures(email: str) -> None:
    cache.delete(_fail_key(email))
    cache.delete(_lock_key(email))
