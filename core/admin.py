from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Message


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'username', 'is_online', 'last_seen', 'is_staff')
    list_filter = ('is_online', 'is_staff', 'is_active')
    search_fields = ('email', 'username')
    ordering = ('email',)

    fieldsets = UserAdmin.fieldsets + (
        ('Chat Status', {'fields': ('is_online', 'last_seen')}),
    )


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'content', 'timestamp', 'is_read')
    list_filter = ('is_read', 'timestamp')
    search_fields = ('content', 'sender__username', 'receiver__username')
    ordering = ('-timestamp',)
