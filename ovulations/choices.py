from django.db import models

class CyclePhaseType(models.TextChoices):
    MENSTRUAL = "menstrual", "Menstrual"
    FOLLICULAR = "follicular", "Follicular"
    OVULATION = "ovulation", "Ovulation"
    LUTEAL = "luteal", "Luteal"

class InsightType(models.TextChoices):
    CYCLE = "CYCLE", "Cycle Insight"
    AFFIRMATION = "AFFIRMATION", "Affirmation"
    TIP = "TIP", "Health Tip"
    
class PeriodRegularity(models.TextChoices):
    REGULAR = "regular", "Regular"
    IRREGULAR = "irregular", "Irregular"
    PREFER_NOT_TO_SAY = "prefer_not_to_say", "Prefer not to say"
    
class ConfidenceType(models.TextChoices):
    LOW = "low", "Low"
    MID = "mid", "Mid"
    HIGH = "high", "High"