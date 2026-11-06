from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.faqs.views import AskView, ChatLogViewSet

router = DefaultRouter()
router.register(r"chat-logs", ChatLogViewSet, basename="chatlog")

urlpatterns = [
    path("ask/", AskView.as_view(), name="faq-ask"),
] + router.urls
