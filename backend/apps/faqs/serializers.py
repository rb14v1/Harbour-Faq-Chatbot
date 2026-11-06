from rest_framework import serializers

from apps.faqs.models import ChatLog, FAQEntry


class FAQEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQEntry
        fields = ["id", "question", "answer", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_question(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Question cannot be blank.")
        return value

    def validate_answer(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Answer cannot be blank.")
        return value


class ChatLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatLog
        fields = ["id", "question_asked", "generated_answer", "matched_faq_ids", "created_at"]
        read_only_fields = fields


class AskRequestSerializer(serializers.Serializer):
    question = serializers.CharField(allow_blank=False, trim_whitespace=True)


class MatchedFAQSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    question = serializers.CharField()
    answer = serializers.CharField()
    score = serializers.FloatField()


class AskResponseSerializer(serializers.Serializer):
    answer = serializers.CharField()
    matched_faqs = MatchedFAQSerializer(many=True)
