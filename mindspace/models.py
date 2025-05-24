from django.db import models

from accounts.models import User
from common.models import BaseModel
from mindspace.choices import MindSpaceFrequencyType

class MindSpaceQA(BaseModel):
    """
    Represents a mind space.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="mind_space_qa")
    frequency_type = models.CharField(default=MindSpaceFrequencyType.Daily, choices=MindSpaceFrequencyType, max_length=50)
    goals = models.JSONField(default=list, blank=True) 

    def __str__(self):
        return f'{self.user.email} - Mind Space'

    class Meta:
        verbose_name = "Mind Space"
        verbose_name_plural = "Mind Spaces"