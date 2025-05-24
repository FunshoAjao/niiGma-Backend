from django.db import models

    
class MindSpaceFrequencyType(models.TextChoices):
    Daily = "daily", "Daily"
    Weekly = "weekly", "Weekly"
    Monthly = "monthly", "Monthly"
    Yearly = "yearly", "Yearly"
    Occasionally = "occasionally", "Occasionally"
    Never = "never", "Never"
    Rarely = "rarely", "Rarely"