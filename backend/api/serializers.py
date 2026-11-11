from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import Announcement, AnnouncementComment, LiturgicalReading, MassRequest, MassSchedule, NotificationGroup, ParishNotification, UserProfile, PrivateMessage, ParishGroupMessage
from django.contrib.auth.models import User

class NotificationGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationGroup
        fields = ['id', 'name']

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']

class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    group = NotificationGroupSerializer(read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True)
    parish_entities = NotificationGroupSerializer(many=True, read_only=True)
    parish_entity_names = serializers.SerializerMethodField()

    def get_parish_entity_names(self, profile):
        names = list(profile.parish_entities.order_by('name').values_list('name', flat=True))
        if not names and profile.group_id:
            names.append(profile.group.name)
        return names

    class Meta:
        model = UserProfile
        fields = [
            'id', 'user', 'phone_number', 'first_name', 'last_name', 'group',
            'group_name', 'parish_entities', 'parish_entity_names', 'otp_verified',
        ]


class MessagingProfileSerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(source='group.name', read_only=True)
    parish_entity_names = serializers.SerializerMethodField()

    def get_parish_entity_names(self, profile):
        names = list(profile.parish_entities.order_by('name').values_list('name', flat=True))
        if not names and profile.group_id:
            names.append(profile.group.name)
        return names

    class Meta:
        model = UserProfile
        fields = ['id', 'first_name', 'last_name', 'group_name', 'parish_entity_names']

class AnnouncementSerializer(serializers.ModelSerializer):
    target_groups = NotificationGroupSerializer(many=True, read_only=True)
    video_url = serializers.SerializerMethodField()
    media_url = serializers.SerializerMethodField()
    media_type = serializers.SerializerMethodField()
    comments_count = serializers.IntegerField(read_only=True)
    likes_count = serializers.IntegerField(read_only=True)
    shares_count = serializers.IntegerField(read_only=True)
    is_liked = serializers.BooleanField(read_only=True)

    class Meta:
        model = Announcement
        fields = [
            'id',
            'title',
            'body',
            'announcement_type',
            'created_at',
            'published_at',
            'link_url',
            'link_title',
            'target_groups',
            'image_url',
            'video_url',
            'media_url',
            'media_type',
            'comments_count',
            'likes_count',
            'shares_count',
            'is_liked',
        ]

    def get_video_url(self, announcement):
        if announcement.media_file and announcement.media_file.name.lower().endswith(('.mp4', '.m4v', '.mov', '.webm')):
            return self.get_file_url(announcement)
        return announcement.video_url

    def get_media_url(self, announcement):
        if announcement.media_file:
            return self.get_file_url(announcement)
        return announcement.video_url or announcement.image_url

    def get_media_type(self, announcement):
        if announcement.media_file:
            return 'video' if announcement.media_file.name.lower().endswith(('.mp4', '.m4v', '.mov', '.webm')) else 'image'
        if announcement.video_url:
            return 'video'
        if announcement.image_url:
            return 'image'
        return ''

    def get_file_url(self, announcement):
        url = announcement.media_file.url
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(url)
        return url


class AnnouncementCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = AnnouncementComment
        fields = ['id', 'author_name', 'body', 'created_at']
        read_only_fields = ['id', 'author_name', 'created_at']

    def get_author_name(self, comment):
        return f'{comment.author.first_name} {comment.author.last_name}'.strip() or 'Fidèle paroissial'


class CreateAnnouncementCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnnouncementComment
        fields = ['body']

    def validate_body(self, value):
        body = value.strip()
        if not body:
            raise serializers.ValidationError('Le commentaire ne peut pas être vide.')
        return body


class LiturgicalReadingSerializer(serializers.ModelSerializer):
    class Meta:
        model = LiturgicalReading
        fields = ['id', 'date', 'title', 'content', 'source']


class MassScheduleSerializer(serializers.ModelSerializer):
    weekday_label = serializers.CharField(source='get_weekday_display', read_only=True)

    class Meta:
        model = MassSchedule
        fields = ['id', 'weekday', 'weekday_label', 'date', 'time', 'location']


def validate_voice_message(upload):
    allowed_types = {
        'audio/mp4',
        'audio/m4a',
        'audio/aac',
        'audio/mpeg',
        'audio/ogg',
        'audio/webm',
        'audio/wav',
        'audio/x-wav',
    }
    if upload.size > 8 * 1024 * 1024:
        raise serializers.ValidationError('Un message vocal ne peut pas dépasser 8 Mo.')
    if getattr(upload, 'content_type', '') not in allowed_types:
        raise serializers.ValidationError('Format vocal non pris en charge.')


class MassRequestSerializer(serializers.ModelSerializer):
    requester = UserProfileSerializer(read_only=True)
    phone = serializers.CharField(max_length=20, required=True, allow_blank=False, trim_whitespace=True)
    locality = serializers.CharField(max_length=200, required=True, allow_blank=False, trim_whitespace=True)

    class Meta:
        model = MassRequest
        fields = ['id', 'requester', 'phone', 'contact_email', 'locality', 'preferred_date', 'message', 'status', 'created_at']


class ParishNotificationSerializer(serializers.ModelSerializer):
    mass_request_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = ParishNotification
        fields = ['id', 'kind', 'title', 'message', 'mass_request_id', 'created_at']


class PrivateMessageSerializer(serializers.ModelSerializer):
    sender = MessagingProfileSerializer(read_only=True)
    recipient = MessagingProfileSerializer(read_only=True)
    recipient_id = serializers.PrimaryKeyRelatedField(
        source='recipient', queryset=UserProfile.objects.filter(otp_verified=True), write_only=True
    )
    audio_url = serializers.SerializerMethodField()
    audio = serializers.FileField(required=False, write_only=True)
    body = serializers.CharField(max_length=2000, required=False, allow_blank=True)

    class Meta:
        model = PrivateMessage
        fields = ['id', 'sender', 'recipient', 'recipient_id', 'body', 'audio', 'audio_url', 'is_read', 'created_at']

    def get_audio_url(self, message):
        return f'/messagerie/messages/{message.id}/audio/' if message.audio else None

    def validate_audio(self, upload):
        validate_voice_message(upload)
        return upload

    def validate_body(self, value):
        return value.strip()

    def validate(self, attrs):
        if not attrs.get('body') and not attrs.get('audio'):
            raise serializers.ValidationError('Ajoutez un texte ou un message vocal.')
        return attrs


class ParishGroupMessageSerializer(serializers.ModelSerializer):
    entity = NotificationGroupSerializer(read_only=True)
    sender = MessagingProfileSerializer(read_only=True)
    audio_url = serializers.SerializerMethodField()

    class Meta:
        model = ParishGroupMessage
        fields = ['id', 'entity', 'sender', 'body', 'audio_url', 'created_at']

    def get_audio_url(self, message):
        return f'/messagerie/entites/messages/{message.id}/audio/' if message.audio else None

    def validate_body(self, value):
        return value.strip()


class ParishGroupMessageCreateSerializer(serializers.Serializer):
    entity_ids = serializers.PrimaryKeyRelatedField(
        queryset=NotificationGroup.objects.all(),
        many=True,
        required=False,
        write_only=True,
    )
    entity_id = serializers.PrimaryKeyRelatedField(
        queryset=NotificationGroup.objects.all(),
        required=False,
        write_only=True,
    )
    body = serializers.CharField(max_length=2000, required=False, allow_blank=True)
    audio = serializers.FileField(required=False, write_only=True)

    def validate(self, data):
        if not data.get('body', '').strip() and not data.get('audio'):
            raise serializers.ValidationError('Ajoutez un texte ou un message vocal.')
        if data.get('audio'):
            validate_voice_message(data['audio'])
        entities = data.get('entity_ids')
        if entities is None and data.get('entity_id') is not None:
            entities = [data['entity_id']]
        if not entities:
            raise serializers.ValidationError({
                'entity_ids': 'Sélectionnez au moins une entité paroissiale.'
            })
        entity_ids = {entity.id for entity in entities}
        data['entities'] = list(NotificationGroup.objects.filter(id__in=entity_ids).order_by('name'))
        data['body'] = data.get('body', '').strip()
        return data

class RequestOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20, required=False)
    phone = serializers.CharField(max_length=20, required=False)

    def validate(self, data):
        phone = data.get('phone_number') or data.get('phone')
        if not phone:
            raise serializers.ValidationError({'phone_number': 'Ce champ est obligatoire.'})
        data['phone_number'] = phone
        return data


class VerifyOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20, required=False)
    phone = serializers.CharField(max_length=20, required=False)
    otp_code = serializers.CharField(max_length=6)

    def validate(self, data):
        phone = data.get('phone_number') or data.get('phone')
        if not phone:
            raise serializers.ValidationError({'phone_number': 'Ce champ est obligatoire.'})
        data['phone_number'] = phone
        return data


class PasswordResetRequestSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20, required=False)
    phone = serializers.CharField(max_length=20, required=False)

    def validate(self, data):
        phone_number = data.get('phone_number') or data.get('phone')
        if not phone_number:
            raise serializers.ValidationError({'phone_number': 'Ce champ est obligatoire.'})
        data['phone_number'] = phone_number.strip()
        return data


class PasswordResetConfirmSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)
    otp_code = serializers.RegexField(r'^\d{6}$')
    new_password = serializers.CharField(write_only=True, min_length=6)


class RegisterSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    phone_number = serializers.CharField(max_length=20)
    group_name = serializers.CharField(max_length=100, required=False)
    parish_entity_names = serializers.ListField(
        child=serializers.CharField(max_length=100, allow_blank=False),
        required=False,
        allow_empty=False,
        max_length=12,
    )
    password = serializers.CharField(write_only=True, min_length=6)

    def validate(self, data):
        entity_names = data.get('parish_entity_names')
        if entity_names is None:
            legacy_name = data.get('group_name', '').strip()
            if not legacy_name:
                raise serializers.ValidationError({
                    'parish_entity_names': 'Sélectionnez au moins une entité paroissiale.'
                })
            entity_names = [legacy_name]
        normalized_names = list(dict.fromkeys(name.strip() for name in entity_names if name.strip()))
        if not normalized_names:
            raise serializers.ValidationError({
                'parish_entity_names': 'Sélectionnez au moins une entité paroissiale.'
            })
        data['parish_entity_names'] = normalized_names
        return data

    def validate_phone_number(self, value):
        user = User.objects.filter(username=value).first()
        if user is not None and user.has_usable_password():
            raise serializers.ValidationError('Ce numéro est déjà utilisé.')
        if UserProfile.objects.filter(phone_number=value).exclude(user=user).exists():
            raise serializers.ValidationError('Ce numéro est déjà utilisé.')
        return value


class LoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(username=data['phone_number'], password=data['password'])
        if user is None:
            raise serializers.ValidationError('Numéro de téléphone ou mot de passe incorrect.')
        data['user'] = user
        return data
