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