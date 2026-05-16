from django.contrib import admin

from .models import Investment, PortfolioSnapshot, Tracking

admin.site.register(Tracking)
admin.site.register(Investment)
admin.site.register(PortfolioSnapshot)
