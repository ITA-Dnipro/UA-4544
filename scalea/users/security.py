from django.core.cache import cache


MAX_FAILED_ATTEMPTS = 5
LOCKOUT_SECONDS = 15 * 60


PASSWORD_RESET_MAX_ATTEMPTS = 5
PASSWORD_RESET_WINDOW_SECONDS = 3600



def _fail_key(email: str) -> str:
    return f'auth:login:fail:{email}'


def _lock_key(email: str) -> str:
    return f'auth:login:lock:{email}'


def is_locked(email: str) -> bool:
    """Перевіряє, чи заблоковано вхід для цього email"""
    return bool(cache.get(_lock_key(email)))


def register_failure(email: str) -> None:
    """Реєструє невдалу спробу входу"""
    key = _fail_key(email)
    count = int(cache.get(key, 0)) + 1
    cache.set(key, count, timeout=LOCKOUT_SECONDS)
    if count >= MAX_FAILED_ATTEMPTS:
        cache.set(_lock_key(email), True, timeout=LOCKOUT_SECONDS)


def clear_failures(email: str) -> None:
    """Очищує лічильник невдалих спроб входу"""
    cache.delete(_fail_key(email))
    cache.delete(_lock_key(email))



def _pr_count_key(email: str) -> str:
    """Ключ для підрахунку спроб скидання пароля"""
    return f'auth:password_reset:count:{email}'


def _pr_lock_key(email: str) -> str:
    """Ключ для блокування скидання пароля"""
    return f'auth:password_reset:lock:{email}'


def is_password_reset_locked(email: str) -> bool:
    """Перевіряє, чи заблоковано запити на скидання пароля для цього email"""
    return bool(cache.get(_pr_lock_key(email)))


def register_password_reset_request(email: str) -> None:
    """Реєструє спробу запиту на скидання пароля"""
    count_key = _pr_count_key(email)
    try:
        count = cache.incr(count_key)
    except ValueError:
        cache.set(count_key, 1, timeout=PASSWORD_RESET_WINDOW_SECONDS)
        count = 1

    if count >= PASSWORD_RESET_MAX_ATTEMPTS:
        cache.set(_pr_lock_key(email), True, timeout=PASSWORD_RESET_WINDOW_SECONDS)