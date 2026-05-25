from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0003_project_admin_moderation_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='tags',
            field=models.JSONField(blank=True, default=list),
        ),
    ]
