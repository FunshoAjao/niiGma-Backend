from django.db import models


class BiologicalSex(models.TextChoices):
    MALE = "male", "Male"
    FEMALE = "female", "Female"
    Others = "others", "Others"
