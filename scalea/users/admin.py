from django.contrib import admin

from .models import PasswordResetAudit, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'email',
        'is_startup',
        'is_investor',
        'is_verified',
        'is_active',
    )
    search_fields = ('email',)


@admin.register(PasswordResetAudit)
class PasswordResetAuditAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'email',
        'user',
        'created_at',
        'expires_at',
        'used_at',
        'revoked',
    )
    list_filter = ('revoked', 'created_at', 'expires_at', 'used_at')
    search_fields = ('email', 'user__email', 'token_hash')
    readonly_fields = ('created_at',)

    actions = ['revoke_selected_tokens']

    @admin.action(description='Revoke selected password reset tokens')
    def revoke_selected_tokens(self, request, queryset):
        updated = queryset.filter(
            token_hash__isnull=False,
            revoked=False,
            used_at__isnull=True,
        ).update(revoked=True)
        self.message_user(request, f'{updated} token(s) revoked.')
