from django.contrib import admin
from .models import FeverTriggers, SensationDescription, SymptomSession, SymptomLocation, Symptom, SymptomAnalysis


@admin.register(SymptomSession)
class SymptomSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'biological_sex', 'age', 'created_at')
    search_fields = ('user__username', 'user__email')
    list_filter = ('biological_sex', 'created_at')
    ordering = ('-created_at',)


@admin.register(SymptomLocation)
class SymptomLocationAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'body_area', 'created_at')
    search_fields = ('body_area', 'session__user__username')
    list_filter = ('body_area',)
    ordering = ('-created_at',)


@admin.register(Symptom)
class SymptomAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'get_symptom_names', 'severity', 'started_on', 'created_at')
    search_fields = ('body_areas', 'symptom_names')
    list_filter = ('severity', 'sensation', 'started_on')
    ordering = ('-created_at',)

    def get_symptom_names(self, obj):
        return ", ".join(obj.symptom_names)
    get_symptom_names.short_description = 'Symptoms'


@admin.register(SymptomAnalysis)
class SymptomAnalysisAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'created_at')
    search_fields = ('session__user__username',)
    readonly_fields = ('user_report',)
    ordering = ('-created_at',)

@admin.register(SensationDescription)
class SensationDescriptionAdmin(admin.ModelAdmin):
    list_display = ("id", "description")
    search_fields = ("description",)


@admin.register(FeverTriggers)
class FeverTriggersAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)