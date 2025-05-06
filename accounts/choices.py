from django.db import models


class Gender(models.TextChoices):
    MALE = "male", "Male"
    FEMALE = "female", "Female"
    PREFER_NOT_TO_SAY = "prefer_not_to_say", "Prefer not to say"
    Others = "others", "Others"
    