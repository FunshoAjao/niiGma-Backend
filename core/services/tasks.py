import json
from django.utils.timezone import now
from datetime import date
from django.db.models import Sum

class MindSpaceAIAssistant:
    def __init__(self, user):
        self.user = user
