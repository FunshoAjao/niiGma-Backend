from django.contrib import admin
from .models import CycleSetup, OvulationCycle, OvulationLog, CycleState, CycleInsight

@admin.register(CycleSetup)
class CycleSetupAdmin(admin.ModelAdmin):
    search_fields = ('user__email', 'first_period_date')
    list_display = ('user__email', 'first_period_date', 'setup_complete')
    ordering = ('-created_at',)
    list_filter = ('user__email',)
    
@admin.register(OvulationCycle)
class OvulationCycleAdmin(admin.ModelAdmin):
    search_fields = ('user__email', 'cycle_length')
    list_display = ('user__email', 'cycle_length', 'period_length', 'start_date', 'end_date', 'is_predicted')
    ordering = ('-created_at',)
    list_filter = ('user__email',)
    
@admin.register(OvulationLog)
class OvulationLogAdmin(admin.ModelAdmin):
    search_fields = ('user__email', 'date', 'symptoms')
    list_display = ('user__email', 'date', 'symptoms')
    ordering = ('-created_at',)
    list_filter = ('user__email',)
    
@admin.register(CycleState)
class CycleStateAdmin(admin.ModelAdmin):
    search_fields = ('user__email', 'day_in_cycle', 'phase', 'regularity')
    list_display = ('user__email', 'day_in_cycle', 'phase', 'regularity', 'created_at')
    ordering = ('-created_at',)
    list_filter = ('user__email',)
    
@admin.register(CycleInsight)
class CycleInsightAdmin(admin.ModelAdmin):
    search_fields = ('user__email', 'phase', 'insight_type')
    list_display = ('user__email', 'phase', 'created_at')
    ordering = ('-created_at',)
    list_filter = ('user__email',)