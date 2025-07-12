from django.db import models

    
class ReminderChoices(models.TextChoices):
    Daily = "daily", "Daily"
    Only_If_I_Forget = "only if I forget", "Only if I forget"
    No_Thanks = "no thanks", "No thanks"
    