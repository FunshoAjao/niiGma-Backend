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
    Scared = "scared", "Scared"
    Teary = "teary", "Teary"
    Hopeful = "hopeful", "Hopeful"
    Tired = "tired", "Tired"
    Upset = "upset", "Upset"
    
class RitualTypeChoices(models.TextChoices):
    Gratitude = "gratitude journaling", "Gratitude Journaling"
    Breathing = "breathing", "Breathing"
    Visualization = "visualization", "Visualization"
    
class TagChoices(models.TextChoices):
    Hope = "hope", "Hope"
    Love = "love", "Love"
    Grief = "grief", "Grief"
    Clarity = "clarity", "Clarity"
    
class CategoryChoices(models.TextChoices):
    SelfCare = "selfcare", "SelfCare"
    Parenting = "parenting", "Parenting"
    Stress = "stress", "Stress"
    Budget = "budget", "Budget"