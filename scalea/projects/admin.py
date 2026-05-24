from django.contrib import admin

from .models import Project, ProjectAudit

admin.site.register(Project)
admin.site.register(ProjectAudit)
