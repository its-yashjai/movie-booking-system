from django.contrib import admin
from django.contrib.auth.models import User
from accounts.models import UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_email_verified', 'email_verified_at', 'created_at')
    list_filter = ('is_email_verified', 'created_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at', 'email_verified_at')
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Verification Status', {
            'fields': ('is_email_verified', 'email_verified_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
