from django.db import models
from accounts.models import User
from common.models import BaseModel
from symptoms.choices import BiologicalSex

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
    location = models.ForeignKey(SymptomLocation, on_delete=models.CASCADE, related_name='symptoms')
    name = models.CharField(max_length=100)  # e.g. "Headache", "Cough"
    description = models.TextField(blank=True)
    started_on = models.CharField(max_length=50)  # e.g. "Yesterday"
    severity = models.CharField(max_length=20)  # e.g. "Mild", "Moderate", "Severe"
    sensation = models.CharField(max_length=50, blank=True)  # e.g. "Stabbing", "Burning"
    worsens_with = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} - {self.location.body_area}"

class SymptomAnalysis(BaseModel):
    session = models.OneToOneField(SymptomSession, on_delete=models.CASCADE, related_name='analysis')
    possible_causes = models.JSONField()  # Store a list of dicts with name, description, probability
    advice = models.TextField(blank=True)

    def __str__(self):
        return f"Analysis for {self.session.user.full_name}"