from django.contrib import admin

from .models import User

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'phone_number', 'email', 'is_active', 'is_staff', 'created_at')
    search_fields = ('phone_number', 'email')
    list_filter = ('is_active', 'is_staff')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)