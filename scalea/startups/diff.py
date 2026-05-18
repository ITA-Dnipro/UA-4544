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


def _profile_snapshot(profile):
    return {field: getattr(profile, field) for field in AUDITED_PROFILE_FIELDS}


def _build_changes(before, after):
    changes = {}
    for field, old_value in before.items():
        new_value = after.get(field)
        if old_value != new_value:
            changes[field] = {'old': old_value, 'new': new_value}
    return changes
