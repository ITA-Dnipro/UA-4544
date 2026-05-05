from django.conf import settings
from django.db import models
from django.utils.text import slugify


class StartupProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    company_name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True, null=True)
    hero_image_url = models.URLField(blank=True)
    logo_url = models.URLField(blank=True)
    short_description = models.CharField(max_length=500, blank=True)
    description = models.TextField(blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=50, blank=True)
    tags = models.JSONField(default=list, blank=True)
    website = models.URLField(blank=True)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='published_profiles',
    )
    draft_saved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            if not self.pk:
                super().save(*args, **kwargs)
            base = slugify(self.company_name)[:245]
            self.slug = f'{base}-{self.pk}'
            return super().save(using=kwargs.get('using'), update_fields=['slug'])
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.company_name
