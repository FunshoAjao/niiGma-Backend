import dateparser
from django.db import models
from accounts.models import User
from common.models import BaseModel
from symptoms.choices import BiologicalSex
from datetime import date

class SymptomSession(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='symptom_sessions')
    biological_sex = models.CharField(max_length=10, choices=BiologicalSex)
    age = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.user.full_name} - {self.created_at.date()}"

class SymptomLocation(BaseModel):
    session = models.ForeignKey(SymptomSession, on_delete=models.CASCADE, related_name='locations')
    body_area = models.CharField(max_length=100)  # e.g. "Head", "Chest", "Back"

    def __str__(self):
        return f"{self.body_area}"

class Symptom(BaseModel):
    session = models.ForeignKey(SymptomSession, on_delete=models.CASCADE, related_name='symptoms', null=True, blank=True)
    body_areas = models.JSONField(default=list)
    symptom_names = models.JSONField()  # A list of strings e.g. "Headache", "Cough"
    description = models.TextField(blank=True)
    started_on = models.CharField(max_length=50)  # e.g. "Yesterday"
    severity = models.CharField(max_length=20)  # e.g. "Mild", "Moderate", "Severe"
    sensation = models.CharField(max_length=50, blank=True)  # e.g. "Stabbing", "Burning"
    worsens_with = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{', '.join(self.body_areas)}: {', '.join(self.symptom_names)}"
    
    def get_duration(self, reference_date=None):
        """
        Returns the duration of the symptom as a human-readable string.
        :param reference_date: Optional; defaults to today. Used to calculate duration from a fixed point.
        """
        if not self.started_on:
            return "N/A"

        started_on_date = dateparser.parse(self.started_on)
        if not started_on_date:
            return "Unknown"

        if not reference_date:
            reference_date = date.today()

        duration_days = (reference_date - started_on_date.date()).days

        if duration_days < 0:
            return "Unknown"

        return f"{duration_days} days" if duration_days != 1 else "1 day"

class SymptomAnalysis(BaseModel):
    session = models.OneToOneField(SymptomSession, on_delete=models.CASCADE, related_name='analysis')
    possible_causes = models.JSONField()  # Store a list of dicts with name, description, probability
    advice = models.TextField(blank=True)

    def __str__(self):
        return f"Analysis for {self.session.user.full_name}"
    
class SensationDescription(models.Model):
    description = models.CharField(max_length=100)
    
    def __str__(self):
        return self.description

class FeverTriggers(models.Model):
    name = models.CharField(max_length=100) 
    
    def __str__(self):
        return self.name