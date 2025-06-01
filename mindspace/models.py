from django.db import models

from accounts.models import User
from common.models import BaseModel
from mindspace.choices import *

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
        
class SoundscapePlay(BaseModel):
    mind_space = models.ForeignKey(MindSpaceProfile, on_delete=models.CASCADE, related_name='soundscape_plays')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.mind_space.user.email} - {self.name}'

class SleepJournalEntry(BaseModel):
    mind_space = models.ForeignKey(MindSpaceProfile, on_delete=models.CASCADE, related_name='sleep_journals')
    date = models.DateField()
    sleep_quality = models.PositiveSmallIntegerField(choices=[(i, i) for i in range(1, 6)])
    reflections = models.TextField(blank=True)

    def __str__(self):
        return f'{self.mind_space.user.email} - {self.date}'

class WindDownRitualLog(BaseModel):
    mind_space = models.ForeignKey(MindSpaceProfile, on_delete=models.CASCADE, related_name='wind_down_rituals')
    ritual_type = models.CharField(max_length=50, choices=RitualTypeChoices)
    completed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.mind_space.user.email} - {self.ritual_type}'
