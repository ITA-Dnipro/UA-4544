# Generated manually for UA-4544

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('startups', '0002_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='startupprofile',
            name='slug',
            field=models.SlugField(blank=True, max_length=255, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='startupprofile',
            name='hero_image_url',
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name='startupprofile',
            name='logo_url',
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name='startupprofile',
            name='short_description',
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name='startupprofile',
            name='contact_email',
            field=models.EmailField(blank=True, max_length=254),
        ),
        migrations.AddField(
            model_name='startupprofile',
            name='contact_phone',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name='startupprofile',
            name='tags',
            field=models.JSONField(blank=True, default=list),
        ),
    ]
