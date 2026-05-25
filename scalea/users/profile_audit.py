from datetime import date, datetime
from decimal import Decimal

from django.db import models
from django.utils.dateparse import parse_date, parse_datetime
from investors.models import InvestorProfile
from startups.models import StartupProfile

STARTUP_AUDITED_PROFILE_FIELDS = [
    'company_name',
    'hero_image_url',
    'logo_url',
    'short_description',
    'description',
    'contact_email',
    'contact_phone',
    'website',
    'tags',
    'is_published',
    'published_at',
    'published_by_id',
]

INVESTOR_AUDITED_PROFILE_FIELDS = [
    'company_name',
    'bio',
    'investment_focus',
    'website',
]


def _json_safe(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def _get_audited_fields(profile):
    if isinstance(profile, StartupProfile):
        return STARTUP_AUDITED_PROFILE_FIELDS
    if isinstance(profile, InvestorProfile):
        return INVESTOR_AUDITED_PROFILE_FIELDS
    return []


def _profile_snapshot(profile):
    return {field: getattr(profile, field) for field in _get_audited_fields(profile)}


def _build_changes(before, after):
    changes = {}
    for field, old_value in before.items():
        new_value = after.get(field)
        if old_value != new_value:
            changes[field] = {
                'old': _json_safe(old_value),
                'new': _json_safe(new_value),
            }
    return changes


def _restore_profile_value(profile, field_name, value):
    if value is None:
        return None

    if field_name.endswith('_id'):
        return value

    field = profile._meta.get_field(field_name)
    if isinstance(field, models.DateTimeField):
        return parse_datetime(value) if isinstance(value, str) else value
    if isinstance(field, models.DateField):
        return parse_date(value) if isinstance(value, str) else value
    if isinstance(field, models.DecimalField):
        return Decimal(value)
    return value
