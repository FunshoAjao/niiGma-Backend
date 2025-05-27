from django.db import models

from accounts.models import User
from common.models import BaseModel
from mindspace.choices import MindSpaceFrequencyType, MoodChoices

class MindSpaceProfile(BaseModel):
    """
    Stores user preferences for the MindSpace section.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="mind_space_profile")
    frequency_type = models.CharField(default=MindSpaceFrequencyType.Daily, choices=MindSpaceFrequencyType, max_length=50)
    goals = models.JSONField(default=list, blank=True) 

    def __str__(self):
        return f'{self.user.email} - Mind Space Profile'

    class Meta:
        verbose_name = "Mind Space"
        verbose_name_plural = "Mind Spaces"

        
class MoodMirrorEntry(BaseModel):
    mind_space = models.ForeignKey(MindSpaceProfile, on_delete=models.CASCADE)
    mood = models.CharField(choices=MoodChoices, max_length=50)
    reflection = models.TextField(help_text="Reflect on your day.")
    title = models.CharField(max_length=255, blank=True, null=True,
                             help_text="Optional title for the entry.")
    date = models.DateTimeField()
    affirmation = models.TextField(
        help_text="Optional affirmation for the entry.",
        blank=True,
        null=True
    )

    class Meta:
        ordering = ['-created_at']