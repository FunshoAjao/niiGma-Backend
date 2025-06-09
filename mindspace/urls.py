from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r'mind_space', MindSpaceViewSet, basename='mind_space')
router.register(r'mood_mirror', MoodMirrorEntryViewSet, basename='mood_mirror')
router.register(r'soundscape', SoundscapePlayViewSet, basename='soundscape')
router.register(r'sleep_journal', SleepJournalEntryViewSet, basename='sleep_journal')
router.register(r'wind_down', WindDownRitualLogViewSet, basename='wind_down')

urlpatterns = router.urls
