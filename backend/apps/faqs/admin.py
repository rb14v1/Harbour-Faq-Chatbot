from django.contrib import admin

from apps.faqs.models import ChatLog, FAQEntry


@admin.register(FAQEntry)
class FAQEntryAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "question", "created_at"]
    search_fields = ["question", "answer"]


@admin.register(ChatLog)
class ChatLogAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "question_asked", "created_at"]
    search_fields = ["question_asked"]
