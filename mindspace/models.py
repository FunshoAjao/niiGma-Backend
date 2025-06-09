from django.db import models
from django.contrib.postgres.fields import ArrayField
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
        
class SoundscapeLibrary(models.Model):
    """
    This Library is exclusive for the admin
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    audio_url = models.URLField()
    duration = models.IntegerField(blank=True, null=True, help_text="Duration in seconds")
    mood_tag = models.CharField(max_length=50, blank=True, null=True)  # e.g., "rain", "forest"
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)  # for weekly curation
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

        
class SoundscapePlay(BaseModel):
    mind_space = models.ForeignKey(MindSpaceProfile, on_delete=models.CASCADE, related_name='soundscape_plays')
    soundscape = models.ForeignKey(SoundscapeLibrary, on_delete=models.CASCADE, blank=True, null=True)
    is_liked = models.BooleanField(default=False)
    played_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    duration_played = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return f"{self.mind_space.user.email} played {self.soundscape.name}"

class SleepJournalEntry(BaseModel):
    mind_space = models.ForeignKey(MindSpaceProfile, on_delete=models.CASCADE, related_name='sleep_journals')
    date = models.DateField()
    sleep_quality = models.PositiveSmallIntegerField(choices=[(i, i) for i in range(1, 6)])
    journal_entry = models.TextField(blank=True)
    sleep_summary = models.TextField(
        null=True, blank=True,
        help_text="How did you sleep last night? E.g., dreams, restfulness, emotions"
    )

    def __str__(self):
        return f'{self.mind_space.user.email} - {self.date}'

class WindDownRitualLog(BaseModel):
    mind_space = models.ForeignKey(MindSpaceProfile, on_delete=models.CASCADE, related_name='wind_down_rituals')
    ritual_type = models.CharField(max_length=50, choices=RitualTypeChoices)
    
    entries = ArrayField(
        base_field=models.TextField(),
        size=3,
        blank=True,
        default=list,
        help_text="E.g., gratitude entries"
    )

    reflection = models.TextField(blank=True, null=True, help_text="Optional reflection text")
    metadata = models.JSONField(blank=True, null=True, help_text="Extra data: e.g., breathing cycles")
    completed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.mind_space.user.email} - {self.ritual_type}'
    
class SoulReflection(BaseModel):
    mind_space = models.ForeignKey(MindSpaceProfile, on_delete=models.SET_NULL, null=True, blank=True)
    reflection = models.TextField()
    tag = models.CharField(max_length=30, choices=TagChoices)
    country = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Reflection from {self.city or 'Somewhere'}"

class ResilienceReplay(BaseModel):
    mind_space = models.ForeignKey(MindSpaceProfile, on_delete=models.CASCADE, related_name='replays')
    message = models.TextField()

    def __str__(self):
        return f"{self.mind_space.user.email} - replay"

class Whisper(BaseModel):
    mind_space = models.ForeignKey(MindSpaceProfile, on_delete=models.CASCADE, related_name='whisper')
    content = models.TextField()
    country = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"Whisper from {self.city or 'Unknown'}"

class ThriveTool(BaseModel):
    title = models.CharField(max_length=100)
    content = models.TextField()
    category = models.CharField(max_length=50, choices=CategoryChoices)

    def __str__(self):
        return f"{self.title} ({self.category})"
