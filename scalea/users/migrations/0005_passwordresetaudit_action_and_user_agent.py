# Generated migration for PasswordResetAudit model updates

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_merge_20260508_1126'),
    ]

    operations = [
        migrations.AddField(
            model_name='passwordresetaudit',
            name='user_agent',
            field=models.CharField(blank=True, default='', max_length=500),
        ),
        migrations.AddField(
            model_name='passwordresetaudit',
            name='action',
            field=models.CharField(
                choices=[
                    ('requested', 'Password Reset Requested'),
                    ('confirmed', 'Password Reset Confirmed'),
                ],
                default='requested',
                help_text='Action performed: request or confirmation',
                max_length=20,
            ),
        ),
    ]
