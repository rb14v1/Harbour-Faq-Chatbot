from rest_framework.routers import DefaultRouter

from apps.faqs.views import FAQEntryViewSet

router = DefaultRouter()
router.register(r"", FAQEntryViewSet, basename="faqentry")

urlpatterns = router.urls
