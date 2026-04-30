from django.contrib import admin

from .models import PasswordResetAuditLog, PasswordResetToken, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['email', 'username', 'is_startup', 'is_investor', 'is_verified', 'created_at']
    list_filter = ['is_startup', 'is_investor', 'is_verified', 'created_at']
    search_fields = ['email', 'username']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'is_used', 'created_at', 'used_at']
    list_filter = ['is_used', 'created_at']
    search_fields = ['user__email']
    readonly_fields = ['created_at', 'used_at', 'token_hash']


@admin.register(PasswordResetAuditLog)
class PasswordResetAuditLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'ip_address', 'created_at']
    list_filter = ['action', 'created_at']
    search_fields = ['user__email', 'ip_address']
    readonly_fields = ['created_at', 'user', 'action', 'ip_address', 'user_agent', 'details']
