from django.contrib import admin

from .models import PromptHistory, User

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'phone_number', 'email', 'is_active', 'is_staff', 'created_at')
    search_fields = ('phone_number', 'email')
    list_filter = ('is_active', 'is_staff')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
    
@admin.register(PromptHistory)
class PromptHistoryAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'section',
        'conversation_id',
        'short_prompt',
        'short_response',
        'created_at',
    )
    list_filter = ('section', 'created_at')
    search_fields = ('user__email', 'prompt', 'response', 'conversation_id')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)

    def short_prompt(self, obj):
        return (obj.prompt[:75] + '...') if len(obj.prompt) > 75 else obj.prompt
    short_prompt.short_description = 'Prompt'

    def short_response(self, obj):
        return (obj.response[:75] + '...') if len(obj.response) > 75 else obj.response
    short_response.short_description = 'Response'