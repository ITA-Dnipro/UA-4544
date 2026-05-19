from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('startups', '0004_startupprofile_draft_saved_at_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProfileAudit',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('changes', models.JSONField(blank=True, default=dict)),
                (
                    'profile',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='audit_entries',
                        to='startups.startupprofile',
                    ),
                ),
                (
                    'user',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='profile_audits',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'ordering': ['-timestamp'],
            },
        ),
    ]
