from collections import Counter

password_reset_metrics = Counter()


def inc_reset_request():
    password_reset_metrics['password_reset.requests'] += 1


def inc_reset_confirm():
    password_reset_metrics['password_reset.confirms'] += 1


def inc_reset_expired_attempt():
    password_reset_metrics['password_reset.expired_attempts'] += 1


def inc_reset_reused_attempt():
    password_reset_metrics['password_reset.reused_attempts'] += 1
