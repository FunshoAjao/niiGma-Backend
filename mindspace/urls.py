from rest_framework.routers import DefaultRouter
from .views import MoodMirrorEntryViewSet

router = DefaultRouter()
router.register(r'', MoodMirrorEntryViewSet, basename='mood_mirror')

urlpatterns = router.urls
