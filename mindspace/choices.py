from django.db import models

    
class MindSpaceFrequencyType(models.TextChoices):
    Daily = "daily", "Daily"
    Weekly = "weekly", "Weekly"
    Monthly = "monthly", "Monthly"
    Yearly = "yearly", "Yearly"
    Occasionally = "occasionally", "Occasionally"
    Never = "never", "Never"
    Rarely = "rarely", "Rarely"
    
class MoodChoices(models.TextChoices):
    Happy = "happy", "Happy"
    Sad = "sad", "Sad"
    Angry = "angry", "Angry"
    Anxious = "anxious", "Anxious"
    Excited = "excited", "Excited"
    Calm = "calm", "Calm"
    Frustrated = "frustrated", "Frustrated"
    Confused = "confused", "Confused"
    Bored = "bored", "Bored"
    Motivated = "motivated", "Motivated"
    Overwhelmed = "overwhelmed", "Overwhelmed"
    Relaxed = "relaxed", "Relaxed"
    Grateful = "grateful", "Grateful"
    Hopeful = "hopeful", "Hopeful"
    Lonely = "lonely", "Lonely"
    Tired = "tired", "Tired"
    Inspired = "inspired", "Inspired"
    Curious = "curious", "Curious"
    
class RitualTypeChoices(models.TextChoices):
    Gratitude = "gratitude journaling", "Gratitude Journaling"
    Breathing = "breathing", "Breathing"
    Visualization = "visualization", "Visualization"
    