from django.core.cache import cache

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_SECONDS = 15 * 60
PASSWORD_RESET_MAX_ATTEMPTS = 5
PASSWORD_RESET_WINDOW_SECONDS = 60 * 60  # 1 hour


def _pr_count_key(email: str) -> str:
    return f'auth:password_reset:count:{email}'


def _pr_lock_key(email: str) -> str:
    return f'auth:password_reset:lock:{email}'


def _fail_key(email: str) -> str:
    return f'auth:login:fail:{email}'


def _lock_key(email: str) -> str:
    return f'auth:login:lock:{email}'


def is_locked(email: str) -> bool:
    return bool(cache.get(_lock_key(email)))


def is_password_reset_locked(email: str) -> bool:
    return bool(cache.get(_pr_lock_key(email)))


def register_failure(email: str) -> None:
    key = _fail_key(email)
    count = int(cache.get(key, 0)) + 1
    cache.set(key, count, timeout=LOCKOUT_SECONDS)
    if count >= MAX_FAILED_ATTEMPTS:
        cache.set(_lock_key(email), True, timeout=LOCKOUT_SECONDS)


def register_password_reset_request(email: str) -> None:
    key = _pr_count_key(email)
    count = int(cache.get(key, 0)) + 1
    cache.set(key, count, timeout=PASSWORD_RESET_WINDOW_SECONDS)
    if count >= PASSWORD_RESET_MAX_ATTEMPTS:
        cache.set(_pr_lock_key(email), True, timeout=PASSWORD_RESET_WINDOW_SECONDS)


def clear_failures(email: str) -> None:
    cache.delete(_fail_key(email))
    cache.delete(_lock_key(email))
