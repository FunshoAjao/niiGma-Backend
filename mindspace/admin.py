from django.contrib import admin

from .models import *

@admin.register(SoundscapeLibrary)
class SoundscapeLibraryAdmin(admin.ModelAdmin):
    search_fields = ('name', 'description')
    list_display = ('name', 'description')
    ordering = ('-created_at',) 
    
@admin.register(MindSpaceProfile)
class SoundscapeLibraryAdmin(admin.ModelAdmin):
    search_fields = ('goals',)
    list_display = ( 'goals',)
    ordering = ('-created_at',) 
    
@admin.register(MoodMirrorEntry)
class MoodMirrorEntryAdmin(admin.ModelAdmin):
    search_fields = ('mind_space', 'title')
    list_display = ('mind_space', 'title')
    ordering = ('-created_at',) 
    
@admin.register(SoundscapePlay)
class SoundscapePlayAdmin(admin.ModelAdmin):
    search_fields = ('mind_space', 'soundscape')
    list_display = ( 'mind_space', 'soundscape')
    ordering = ('-created_at',) 
    
@admin.register(WindDownRitualLog)
class WindDownRitualLogAdmin(admin.ModelAdmin):
    search_fields = ('mind_space', 'reflection', 'ritual_type')
    list_display = ( 'mind_space', 'ritual_type')
    ordering = ('-created_at',) 
    
@admin.register(SoulReflection)
class SoulReflectionAdmin(admin.ModelAdmin):
    search_fields = ('mind_space', 'tag', 'reflection')
    list_display = ( 'mind_space', 'tag')
    ordering = ('-created_at',) 