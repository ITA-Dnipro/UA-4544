from django.core.cache import cache

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_SECONDS = 15 * 60


def _fail_key(email: str) -> str:
    return f'auth:login:fail:{email}'


def _lock_key(email: str) -> str:
    return f'auth:login:lock:{email}'


def is_locked(email: str) -> bool:
    return bool(cache.get(_lock_key(email)))


def register_failure(email: str) -> None:
    key = _fail_key(email)
    count = int(cache.get(key, 0)) + 1
    cache.set(key, count, timeout=LOCKOUT_SECONDS)
    if count >= MAX_FAILED_ATTEMPTS:
        cache.set(_lock_key(email), True, timeout=LOCKOUT_SECONDS)


def clear_failures(email: str) -> None:
    cache.delete(_fail_key(email))
    cache.delete(_lock_key(email))
