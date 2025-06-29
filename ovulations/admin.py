from django.contrib import admin
from .models import CycleSetup, OvulationCycle, OvulationLog, CycleState, CycleInsight

admin.site.register(CycleSetup)
admin.site.register(OvulationCycle)
admin.site.register(OvulationLog)
admin.site.register(CycleState)
admin.site.register(CycleInsight)