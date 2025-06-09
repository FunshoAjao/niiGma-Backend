from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r'mind_space', MindSpaceViewSet, basename='mind_space')
router.register(r'mood_mirror', MoodMirrorEntryViewSet, basename='mood_mirror')
router.register(r'soundscape', SoundscapePlayViewSet, basename='soundscape')
router.register(r'sleep_journal', SleepJournalEntryViewSet, basename='sleep_journal')
router.register(r'wind_down', WindDownRitualLogViewSet, basename='wind_down')
router.register(r'soul_reflection', SoulReflectionViewSet, basename='soul_reflection')
router.register(r'replays', ResilienceReplayViewSet, basename='resilience_replay')
router.register(r'whispers', WhisperViewSet, basename='whispers')
router.register(r'thrive_tool', ThriveToolViewSet, basename='thrive_tool')

urlpatterns = router.urls
