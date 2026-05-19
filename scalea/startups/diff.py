from datetime import date, datetime
from decimal import Decimal

AUDITED_PROFILE_FIELDS = [
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


def _json_safe(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def _profile_snapshot(profile):
    return {field: getattr(profile, field) for field in AUDITED_PROFILE_FIELDS}


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
