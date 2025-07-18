from django.db import models
from accounts.models import User
from common.models import BaseModel
from ovulations.choices import CyclePhaseType
from datetime import timedelta

from .choices import InsightType, PeriodRegularity

class CycleSetup(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="cycle_setup_records")
    first_period_date = models.DateField(blank=True, null=True)
    period_length = models.PositiveIntegerField(blank=True, null=True)
    cycle_length = models.PositiveIntegerField(blank=True, null=True)
    regularity = models.CharField(
        max_length=20,
        choices=PeriodRegularity.choices,
        default=PeriodRegularity.REGULAR,
    )
    setup_complete = models.BooleanField(default=False)
    current_focus = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Ovulation Profile for {self.user.email}"
    
    @property
    def ovulation_day(self):
        return self.created_at + timedelta(days=self.cycle_length // 2)

class OvulationCycle(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ovulation_cycles")
    start_date = models.DateField()
    end_date = models.DateField()
    cycle_length = models.PositiveIntegerField(help_text="Length in days")
    period_length = models.PositiveIntegerField(help_text="Menstrual period length in days")
    is_predicted = models.BooleanField(default=True)

    class Meta:
        ordering = ["-start_date"]
        
    def __str__(self):
        return f"Cycle for {self.user.email}"

class OvulationLog(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ovulation_logs")
    date = models.DateField()
    flow = models.CharField(max_length=50)
    symptoms = models.JSONField(default=list, blank=True)  
    mood = models.CharField(max_length=50, blank=True, null=True)
    notes = models.TextField(blank=True)
    discharge = models.CharField(max_length=50, blank=True, null=True)
    sexual_activity = models.CharField(max_length=50, blank=True, null=True)
        
    def __str__(self):
        return f"Log for {self.user.email} on {self.date.isoformat()}"

class CycleState(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="cycle_states")
    date = models.DateField()
    day_in_cycle = models.PositiveIntegerField()
    phase = models.CharField(max_length=20, choices=CyclePhaseType)
    days_to_next_phase = models.PositiveIntegerField()
    average_cycle_length = models.PositiveIntegerField()
    average_period_length = models.PositiveIntegerField()
    regularity = models.CharField(max_length=50)
    total_months_tracked = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ["user", "date"]
        
    def __str__(self):
        return f"Cycle State for {self.user.email} on {self.date.isoformat()}"

class CycleInsight(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    phase = models.CharField(max_length=20, choices=CyclePhaseType)
    confidence = models.CharField(max_length=20)
    headline = models.CharField(max_length=200)
    detail = models.TextField()
    insight_type = models.CharField(max_length=20, choices=InsightType, default="CYCLE")

    indexes = [
        models.Index(fields=["user", "date"]),
    ]
    
    def __str__(self):
        return f"Insight for {self.user.email} on {self.date.isoformat()} - {self.phase}"