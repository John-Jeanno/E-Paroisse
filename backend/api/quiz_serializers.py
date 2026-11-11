from rest_framework import serializers

from .models import QuizChallenge, QuizQuestion, QuizSession, UserProfile


class QuizQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizQuestion
        fields = ['id', 'category', 'prompt', 'options']


class QuizSessionCreateSerializer(serializers.Serializer):
    mode = serializers.ChoiceField(choices=QuizSession.MODE_CHOICES)
    wait_for_audio_completion = serializers.BooleanField(default=False)


class QuizAnswerSerializer(serializers.Serializer):
    question_id = serializers.IntegerField(min_value=1)
    option_index = serializers.IntegerField(min_value=0, max_value=2)


class OfflineQuizAnswerSerializer(serializers.Serializer):
    question_id = serializers.IntegerField(min_value=1)
    option_index = serializers.IntegerField(min_value=0, max_value=2, allow_null=True)
    timed_out = serializers.BooleanField(default=False)

    def validate(self, attrs):
        if (
            (attrs['timed_out'] and attrs['option_index'] is not None)
            or (not attrs['timed_out'] and attrs['option_index'] is None)
        ):
            raise serializers.ValidationError(
                'Une réponse expirée ne peut pas contenir de choix, et une réponse valide doit en contenir un.'
            )
        return attrs


class OfflineQuizResultSerializer(serializers.Serializer):
    client_session_id = serializers.CharField(max_length=64)
    answers = OfflineQuizAnswerSerializer(many=True, min_length=10, max_length=10)

    def validate_answers(self, answers):
        question_ids = [answer['question_id'] for answer in answers]
        if len(question_ids) != len(set(question_ids)):
            raise serializers.ValidationError('Une question ne peut apparaître qu’une seule fois.')
        return answers


class QuizChallengeCreateSerializer(serializers.Serializer):
    recipient_profile_id = serializers.PrimaryKeyRelatedField(
        source='recipient',
        queryset=UserProfile.objects.select_related('user').filter(
            otp_verified=True, user__is_active=True
        ),
    )

    def validate_recipient_profile_id(self, recipient):
        if recipient == self.context['profile']:
            raise serializers.ValidationError('Vous ne pouvez pas vous défier vous-même.')
        if not recipient.otp_verified:
            raise serializers.ValidationError('Ce paroissien ne peut pas recevoir de défi.')
        return recipient
