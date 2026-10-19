from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class VideoflixUserAdmin(UserAdmin):
    """Admin view for users, showing the activation status at a glance."""

    list_display = ('email', 'username', 'is_active', 'is_staff', 'date_joined')
    list_filter = ('is_active', 'is_staff')
    search_fields = ('email', 'username')
    ordering = ('-date_joined',)
    add_fieldsets = UserAdmin.add_fieldsets + ((None, {'fields': ('email',)}),)
