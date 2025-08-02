from django.contrib import admin
from .models import CycleSetup, OvulationCycle, OvulationLog, CycleState, CycleInsight

admin.site.register(CycleSetup)
class CycleSetupAdmin(admin.ModelAdmin):
    search_fields = ('user', 'start_date')
    list_display = ('user', 'start_date', 'end_date')
    ordering = ('-start_date',)
    list_filter = ('user',)
    
admin.site.register(OvulationCycle)
class OvulationCycleAdmin(admin.ModelAdmin):
    search_fields = ('user', 'cycle_length')
    list_display = ('user', 'cycle_length', 'average_cycle_length')
    ordering = ('-created_at',)
    list_filter = ('user',)
    
admin.site.register(OvulationLog)
class OvulationLogAdmin(admin.ModelAdmin):
    search_fields = ('user', 'ovulation_date', 'symptoms')
    list_display = ('user', 'ovulation_date', 'symptoms')
    ordering = ('-created_at',)
    list_filter = ('user',)
    
admin.site.register(CycleState)
class CycleStateAdmin(admin.ModelAdmin):
    search_fields = ('user', 'state')
    list_display = ('user', 'state', 'last_updated')
    ordering = ('-last_updated',)
    list_filter = ('user',)
    
admin.site.register(CycleInsight)
class CycleInsightAdmin(admin.ModelAdmin):
    search_fields = ('user', 'insight')
    list_display = ('user', 'insight', 'created_at')
    ordering = ('-created_at',)
    list_filter = ('user',)