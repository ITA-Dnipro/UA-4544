from django.core.cache import cache

# --- Login per-email protection ---
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_SECONDS = 15 * 60


def _fail_key(email: str) -> str:
    return f'auth:login:fail:{email}'


def _lock_key(email: str) -> str:
    return f'auth:login:lock:{email}'


def is_login_locked(email: str) -> bool:
    return bool(cache.get(_lock_key(email)))


def record_login_failure(email: str) -> None:
    key = _fail_key(email)
    count = int(cache.get(key, 0)) + 1
    cache.set(key, count, timeout=LOCKOUT_SECONDS)
    if count >= MAX_FAILED_ATTEMPTS:
        cache.set(_lock_key(email), True, timeout=LOCKOUT_SECONDS)


def clear_login_failures(email: str) -> None:
    cache.delete(_fail_key(email))
    cache.delete(_lock_key(email))


# --- Registration per-email protection ---
MAX_REGISTER_ATTEMPTS = 5
REGISTER_LOCKOUT_SECONDS = 60 * 60  # 1 hour


def _reg_count_key(email: str) -> str:
    return f'auth:register:count:{email}'


def _reg_lock_key(email: str) -> str:
    return f'auth:register:lock:{email}'


def is_register_locked(email: str) -> bool:
    return bool(cache.get(_reg_lock_key(email)))


def record_register_attempt(email: str) -> None:
    key = _reg_count_key(email)
    count = int(cache.get(key, 0)) + 1
    cache.set(key, count, timeout=REGISTER_LOCKOUT_SECONDS)
    if count >= MAX_REGISTER_ATTEMPTS:
        cache.set(_reg_lock_key(email), True, timeout=REGISTER_LOCKOUT_SECONDS)
