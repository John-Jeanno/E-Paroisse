import os
import mimetypes
import logging
from django.core.files.base import ContentFile
from django.contrib.auth import get_user_model
from django.db import models, transaction
from django.db.models import Count, Exists, F, OuterRef, Q
from django.db.models.functions import Lower
from django.middleware.csrf import get_token
from django.http import FileResponse, Http404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authentication import TokenAuthentication
from rest_framework.throttling import AnonRateThrottle

from .models import Announcement, AnnouncementComment, AnnouncementLike, AnnouncementShare, LiturgicalReading, MassSchedule, DonationSettings, NotificationGroup, OTPRequest, UserProfile, MassRequest, ParishNotification, PrivateMessage, ParishGroupMessage, ParishGroupReadState, QuizQuestion
from .idempotency import idempotent
from .otp import WhatsAppDeliveryError, is_whatsapp_otp_configured, send_whatsapp_otp
from .aelf import fetch_and_cache_reading
from .serializers import (
    AnnouncementSerializer,
    AnnouncementCommentSerializer,
    CreateAnnouncementCommentSerializer,
    LiturgicalReadingSerializer,
    NotificationGroupSerializer,
    RequestOTPSerializer,
    RegisterSerializer,
    LoginSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    UserProfileSerializer,
    VerifyOTPSerializer,
    PrivateMessageSerializer,
    ParishGroupMessageSerializer,
    ParishGroupMessageCreateSerializer,
    MessagingProfileSerializer,
    MassScheduleSerializer,
    ParishNotificationSerializer,
)
from .serializers import MassRequestSerializer
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser

User = get_user_model()
logger = logging.getLogger(__name__)


@method_decorator(ensure_csrf_cookie, name='dispatch')
class CSRFCookieAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({'csrfToken': get_token(request)})


class RequestOTPAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @idempotent
    def post(self, request):
        serializer = RequestOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone_number = serializer.validated_data['phone_number']

        development_console = settings.DEBUG and settings.OTP_PROVIDER == 'console'
        if not development_console and (
            settings.OTP_PROVIDER != 'whatsapp' or not is_whatsapp_otp_configured()
        ):
            return Response(
                {'detail': 'La vérification par WhatsApp n’est pas encore configurée.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        user, created = User.objects.get_or_create(username=phone_number)
        if created:
            user.set_unusable_password()
            user.save()
            UserProfile.objects.create(
                user=user,
                phone_number=phone_number,
                first_name='',
                last_name='',
                otp_verified=False,
            )
        else:
            UserProfile.objects.get_or_create(user=user, defaults={'phone_number': phone_number, 'first_name': '', 'last_name': '', 'otp_verified': False})

        otp_code = OTPRequest.generate_code()
        otp_request = OTPRequest.objects.create(
            phone_number=phone_number,
            code=otp_code,
            purpose='registration',
        )
        try:
            send_otp_message(phone_number, otp_code)
        except WhatsAppDeliveryError:
            logger.exception('Échec de la livraison WhatsApp du code d’inscription.')
            otp_request.used = True
            otp_request.save(update_fields=['used'])
            return Response(
                {'detail': 'Impossible d’envoyer le code de vérification. Réessayez plus tard.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        response_data = {'detail': 'OTP envoyé'}
        if settings.DEBUG:
            response_data['otp_code'] = otp_code

        return Response(response_data, status=status.HTTP_200_OK)


class PasswordResetRequestThrottle(AnonRateThrottle):
    scope = 'password_reset_request'


class PasswordResetConfirmThrottle(AnonRateThrottle):
    scope = 'password_reset_confirm'


class PasswordResetRequestAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetRequestThrottle]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone_number = serializer.validated_data['phone_number']

        development_console = settings.DEBUG and settings.OTP_PROVIDER == 'console'
        if not development_console and (
            settings.OTP_PROVIDER != 'whatsapp' or not is_whatsapp_otp_configured()
        ):
            return Response(
                {'detail': 'La récupération par WhatsApp n’est pas encore configurée. Contactez le secrétariat.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        profile = UserProfile.objects.filter(
            phone_number=phone_number,
            otp_verified=True,
            user__is_active=True,
        ).select_related('user').first()
        response_data = {
            'detail': 'Si ce numéro correspond à un compte vérifié, un code de récupération vous sera envoyé.',
        }
        if profile and profile.user.has_usable_password():
            otp_code = OTPRequest.generate_code()
            if not development_console:
                try:
                    send_whatsapp_otp(phone_number, otp_code)
                except WhatsAppDeliveryError:
                    logger.exception('Échec de la livraison WhatsApp du code de récupération.')
                    return Response(response_data, status=status.HTTP_200_OK)
            OTPRequest.objects.filter(
                phone_number=phone_number,
                purpose='password_reset',
                used=False,
            ).update(used=True)
            OTPRequest.objects.create(
                phone_number=phone_number,
                code=otp_code,
                purpose='password_reset',
            )
            if development_console:
                response_data['otp_code'] = otp_code

        return Response(response_data, status=status.HTTP_200_OK)


class PasswordResetConfirmAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetConfirmThrottle]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        valid_since = timezone.now() - timezone.timedelta(minutes=10)

        with transaction.atomic():
            otp_request = OTPRequest.objects.select_for_update().filter(
                phone_number=data['phone_number'],
                code=data['otp_code'],
                purpose='password_reset',
                used=False,
                created_at__gte=valid_since,
            ).order_by('-created_at').first()
            profile = UserProfile.objects.select_related('user').filter(
                phone_number=data['phone_number'],
                otp_verified=True,
                user__is_active=True,
            ).first()
            if otp_request is None or profile is None or not profile.user.has_usable_password():
                return Response(
                    {'detail': 'Code invalide ou expiré. Demandez un nouveau code.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            otp_request.used = True
            otp_request.save(update_fields=['used'])
            profile.user.set_password(data['new_password'])
            profile.user.save(update_fields=['password'])
            Token.objects.filter(user=profile.user).delete()

        return Response({'detail': 'Mot de passe modifié. Vous pouvez maintenant vous connecter.'})


def send_otp_message(phone_number: str, otp_code: str) -> None:
    provider = settings.OTP_PROVIDER
    if provider == 'whatsapp':
        send_whatsapp_otp(phone_number, otp_code)
    elif provider == 'sms':
        logger.warning('Le fournisseur OTP SMS n’est pas configuré.')
    else:
        logger.warning('Aucun fournisseur OTP n’est configuré.')

class VerifyOTPAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @idempotent
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone_number = serializer.validated_data['phone_number']
        otp_code = serializer.validated_data['otp_code']

        valid_since = timezone.now() - timezone.timedelta(minutes=10)
        otp_request = OTPRequest.objects.filter(
            phone_number=phone_number,
            code=otp_code,
            purpose='registration',
            used=False,
            created_at__gte=valid_since,
        ).order_by('-created_at').first()

        if otp_request is None:
            return Response({'detail': 'OTP invalide ou expiré.'}, status=status.HTTP_400_BAD_REQUEST)

        otp_request.used = True
        otp_request.save()

        user = User.objects.filter(username=phone_number).first()
        if user is None:
            return Response({'detail': 'Utilisateur introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        profile, _ = UserProfile.objects.get_or_create(user=user, defaults={'phone_number': phone_number, 'first_name': '', 'last_name': '', 'otp_verified': True})
        profile.otp_verified = True
        profile.save()

        token, _ = Token.objects.get_or_create(user=user)
        return Response({'token': token.key}, status=status.HTTP_200_OK)


class RegisterAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @idempotent
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        first_name = data['first_name'].strip()
        last_name = data['last_name'].strip()
        entity_names = data['parish_entity_names']

        with transaction.atomic():
            entities = [
                NotificationGroup.objects.get_or_create(name=name)[0]
                for name in entity_names
            ]
            primary_entity = entities[0]
            user, _ = User.objects.get_or_create(username=data['phone_number'])
            user.first_name = first_name
            user.last_name = last_name
            user.set_password(data['password'])
            user.save(update_fields=['first_name', 'last_name', 'password'])
            profile, _ = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'phone_number': data['phone_number'],
                    'first_name': first_name,
                    'last_name': last_name,
                    'group': primary_entity,
                    'otp_verified': True,
                },
            )
            profile.phone_number = data['phone_number']
            profile.first_name = first_name
            profile.last_name = last_name
            profile.group = primary_entity
            profile.otp_verified = True
            profile.save()
            profile.parish_entities.set(entities)
            token, _ = Token.objects.get_or_create(user=user)

        return Response({'token': token.key, 'profile': UserProfileSerializer(profile).data}, status=status.HTTP_201_CREATED)


class LoginAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'token': token.key}, status=status.HTTP_200_OK)

class UserProfileDetail(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile, _ = UserProfile.objects.get_or_create(
            user=request.user,
            defaults={
                'phone_number': request.user.username,
                'first_name': '',
                'last_name': '',
                'otp_verified': True,
            },
        )
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data)

    def put(self, request):
        profile, _ = UserProfile.objects.get_or_create(
            user=request.user,
            defaults={
                'phone_number': request.user.username,
                'first_name': '',
                'last_name': '',
                'otp_verified': True,
            },
        )

        entity_names = request.data.get('parish_entity_names')
        group_name = request.data.get('group_name')
        if entity_names is not None:
            if not isinstance(entity_names, list) or not entity_names or len(entity_names) > 12:
                return Response(
                    {'parish_entity_names': 'Sélectionnez entre une et douze entités paroissiales.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if any(not isinstance(name, str) or len(name.strip()) > 100 for name in entity_names):
                return Response(
                    {'parish_entity_names': 'Chaque entité paroissiale doit avoir au maximum 100 caractères.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            normalized_names = list(dict.fromkeys(
                name.strip() for name in entity_names
                if isinstance(name, str) and name.strip()
            ))
            if not normalized_names:
                return Response(
                    {'parish_entity_names': 'Sélectionnez au moins une entité paroissiale.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            entities = [
                NotificationGroup.objects.get_or_create(name=name)[0]
                for name in normalized_names
            ]
            profile.group = entities[0]
            profile.save()
            profile.parish_entities.set(entities)
        elif group_name is not None:
            group, _ = NotificationGroup.objects.get_or_create(name=group_name.strip())
            profile.group = group
            profile.save()
            profile.parish_entities.set([group])

        profile.first_name = request.data.get('first_name', profile.first_name)
        profile.last_name = request.data.get('last_name', profile.last_name)
        profile.otp_verified = True
        profile.save()

        serializer = UserProfileSerializer(profile)
        return Response(serializer.data)


class ImageUploadAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        file_obj = request.FILES.get('image')
        if not file_obj:
            return Response({'detail': 'Aucun fichier fourni.'}, status=status.HTTP_400_BAD_REQUEST)

        fs = FileSystemStorage(location=str(settings.MEDIA_ROOT))
        filename = fs.save(file_obj.name, file_obj)
        file_url = f"{settings.MEDIA_URL}{filename}"

        return Response({'url': file_url}, status=status.HTTP_201_CREATED)

class NotificationGroupViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = NotificationGroup.objects.order_by(Lower('name'), 'name')
    serializer_class = NotificationGroupSerializer


def visible_announcements_for_user(user):
    queryset = Announcement.objects.filter(published_at__isnull=False)
    if not user.is_authenticated:
        return queryset.filter(target_groups__isnull=True).order_by(
            F('published_at').desc(nulls_last=True), '-created_at'
        )

    profile = UserProfile.objects.filter(user=user).first()
    if profile and (profile.group_id or profile.parish_entities.exists()):
        entity_ids = profile.parish_entities.values_list('id', flat=True)
        if profile.group_id:
            entity_ids = list(entity_ids) + [profile.group_id]
        queryset = queryset.filter(
            Q(target_groups__isnull=True) | Q(target_groups__in=entity_ids)
        )
    else:
        queryset = queryset.filter(target_groups__isnull=True)
    return queryset.distinct().order_by(
        F('published_at').desc(nulls_last=True), '-created_at'
    )


class UserProfileViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = UserProfile.objects.select_related('user', 'group').all()
    serializer_class = UserProfileSerializer


class AnnouncementViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AnnouncementSerializer

    class FeedPagination(PageNumberPagination):
        page_size = 8

    def get_permissions(self):
        if (self.action == 'commentaires' and self.request.method == 'POST') or self.action in ('j_aime', 'partager'):
            return [IsAuthenticated()]
        return super().get_permissions()

    def get_queryset(self):
        queryset = visible_announcements_for_user(self.request.user).prefetch_related('target_groups').annotate(
            comments_count=Count('comments', distinct=True),
            likes_count=Count('likes', distinct=True),
            shares_count=Count('shares', distinct=True),
        )

        if not self.request.user.is_authenticated:
            return queryset.annotate(
                is_liked=models.Value(False, output_field=models.BooleanField())
            )

        profile = UserProfile.objects.filter(user=self.request.user).first()
        if profile:
            queryset = queryset.annotate(
                is_liked=Exists(
                    AnnouncementLike.objects.filter(
                        announcement_id=OuterRef('pk'),
                        user_profile=profile,
                    )
                )
            )
        else:
            queryset = queryset.annotate(is_liked=models.Value(False, output_field=models.BooleanField()))

        return queryset

    @action(detail=False, methods=['get'], url_path='fil')
    def fil(self, request):
        paginator = self.FeedPagination()
        page = paginator.paginate_queryset(self.get_queryset(), request, view=self)
        serializer = self.get_serializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @action(detail=True, methods=['get', 'post'], url_path='commentaires')
    @idempotent
    def commentaires(self, request, pk=None):
        announcement = self.get_object()
        comments = AnnouncementComment.objects.filter(
            announcement=announcement
        ).select_related('author')

        if request.method == 'GET':
            return Response(AnnouncementCommentSerializer(comments, many=True).data)

        profile = UserProfile.objects.filter(user=request.user).first()
        if profile is None:
            return Response(
                {'detail': 'Un profil paroissial est nécessaire pour commenter.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = CreateAnnouncementCommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = serializer.save(announcement=announcement, author=profile)
        return Response(
            AnnouncementCommentSerializer(comment).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'], url_path='j-aime')
    @idempotent
    def j_aime(self, request, pk=None):
        announcement = self.get_object()
        profile = UserProfile.objects.filter(user=request.user).first()
        if profile is None:
            return Response(
                {'detail': 'Un profil paroissial est nécessaire pour aimer une publication.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        desired_state = request.data.get('is_liked')
        if desired_state is not None and not isinstance(desired_state, bool):
            return Response(
                {'is_liked': 'Cette valeur doit être vraie ou fausse.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if desired_state is None:
            like, created = AnnouncementLike.objects.get_or_create(
                announcement=announcement,
                user_profile=profile,
            )
            if not created:
                like.delete()
            is_liked = created
        elif desired_state:
            AnnouncementLike.objects.get_or_create(
                announcement=announcement,
                user_profile=profile,
            )
            is_liked = True
        else:
            AnnouncementLike.objects.filter(
                announcement=announcement,
                user_profile=profile,
            ).delete()
            is_liked = False

        return Response({
            'is_liked': is_liked,
            'likes_count': announcement.likes.count(),
        })

    @action(detail=True, methods=['post'], url_path='partager')
    @idempotent
    def partager(self, request, pk=None):
        announcement = self.get_object()
        profile = UserProfile.objects.filter(user=request.user).first()
        if profile is None:
            return Response(
                {'detail': 'Un profil paroissial est nécessaire pour partager une publication.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        AnnouncementShare.objects.create(
            announcement=announcement,
            user_profile=profile,
        )
        return Response({'shares_count': announcement.shares.count()}, status=status.HTTP_201_CREATED)


class GlobalSearchAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.query_params.get('q', '').strip()
        if len(query) < 2:
            return Response({'detail': 'Saisissez au moins deux caractères.'}, status=status.HTTP_400_BAD_REQUEST)
        if len(query) > 100:
            return Response({'detail': 'La recherche ne peut pas dépasser 100 caractères.'}, status=status.HTTP_400_BAD_REQUEST)

        announcement_results = visible_announcements_for_user(request.user).filter(
            Q(title__icontains=query) | Q(body__icontains=query) | Q(link_title__icontains=query)
        ).prefetch_related('target_groups').annotate(
            comments_count=Count('comments', distinct=True),
            likes_count=Count('likes', distinct=True),
            shares_count=Count('shares', distinct=True),
        )
        profile = UserProfile.objects.filter(user=request.user).first()
        if profile:
            announcement_results = announcement_results.annotate(
                is_liked=Exists(
                    AnnouncementLike.objects.filter(
                        announcement_id=OuterRef('pk'),
                        user_profile=profile,
                    )
                )
            )
        else:
            announcement_results = announcement_results.annotate(
                is_liked=models.Value(False, output_field=models.BooleanField())
            )

        results = [
            {
                'kind': 'announcement',
                'id': str(item.id),
                'title': item.title,
                'subtitle': item.announcement_type,
                'announcement': AnnouncementSerializer(item, context={'request': request}).data,
            }
            for item in announcement_results[:8]
        ]
        results.extend(
            {
                'kind': 'reading',
                'id': str(item.id),
                'title': item.title,
                'subtitle': item.date.isoformat(),
            }
            for item in LiturgicalReading.objects.filter(
                Q(title__icontains=query) | Q(content__icontains=query) | Q(source__icontains=query)
            ).order_by('-date')[:8]
        )
        results.extend(
            {
                'kind': 'question',
                'id': str(item.id),
                'title': item.prompt,
                'subtitle': item.category,
            }
            for item in QuizQuestion.objects.filter(
                is_active=True,
            ).filter(
                Q(prompt__icontains=query) | Q(category__icontains=query)
            ).order_by('id')[:8]
        )

        contacts = UserProfile.objects.select_related('group').filter(
            otp_verified=True,
        ).exclude(
            user=request.user,
        ).filter(
            Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(group__name__icontains=query)
        ).order_by('first_name', 'last_name')[:8]
        results.extend(
            {
                'kind': 'parishioner',
                'id': str(item.id),
                'profile_id': item.id,
                'title': f'{item.first_name} {item.last_name}'.strip() or 'Paroissien',
                'subtitle': item.group.name if item.group_id else 'Paroissien',
            }
            for item in contacts
        )
        return Response(results)


class LiturgicalReadingViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LiturgicalReading.objects.all().order_by('-date')
    serializer_class = LiturgicalReadingSerializer

    def get_queryset(self):
        requested_date = self.request.query_params.get('date')
        if not requested_date:
            return super().get_queryset()

        try:
            day = timezone.datetime.strptime(requested_date, '%Y-%m-%d').date()
        except ValueError:
            return LiturgicalReading.objects.none()

        try:
            fetch_and_cache_reading(day)
        except Exception:
            pass
        return LiturgicalReading.objects.filter(date=day)


class MassRequestAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Admins see all requests; users see their own
        if request.user.is_staff:
            qs = MassRequest.objects.all().order_by('-created_at')
        else:
            profile = UserProfile.objects.filter(user=request.user).first()
            qs = MassRequest.objects.filter(requester=profile).order_by('-created_at')

        serializer = MassRequestSerializer(qs, many=True)
        return Response(serializer.data)

    @idempotent
    def post(self, request):
        serializer = MassRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = UserProfile.objects.filter(user=request.user).first()
        locality = serializer.validated_data['locality']
        if 'ouakam' in locality.casefold():
            name = ' '.join(
                part for part in (profile.first_name, profile.last_name) if part
            ) if profile else ''
            contact_phone = (
                DonationSettings.objects.values_list('parish_contact_phone', flat=True).first()
                or '77 123 45 67'
            )
            greeting = f'{name}, ' if name else ''
            return Response({
                'blocked': True,
                'detail': (
                    f'{greeting}vous ne pouvez pas faire une demande de messe en ligne. '
                    f'Rendez-vous à la paroisse ou appelez le {contact_phone}.'
                ),
                'contact_phone': contact_phone,
            })
        mr = MassRequest.objects.create(
            requester=profile,
            phone=serializer.validated_data.get('phone', ''),
            contact_email=serializer.validated_data.get('contact_email', ''),
            locality=locality,
            preferred_date=serializer.validated_data.get('preferred_date', None),
            message=serializer.validated_data.get('message', ''),
        )
        return Response(MassRequestSerializer(mr).data, status=status.HTTP_201_CREATED)


class MassRequestPaymentInfoAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            'payment_phone': settings.MASS_REQUEST_PAYMENT_PHONE,
            'contact_phone': (
                DonationSettings.objects.values_list('parish_contact_phone', flat=True).first()
                or '77 123 45 67'
            ),
        })


class ParishNotificationsAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = UserProfile.objects.filter(user=request.user).first()
        if profile is None:
            return Response([])
        notifications = ParishNotification.objects.filter(
            recipient=profile,
            is_read=False,
        ).order_by('-created_at')[:100]
        return Response(ParishNotificationSerializer(notifications, many=True).data)

    def post(self, request):
        profile = UserProfile.objects.filter(user=request.user).first()
        if profile is not None:
            ParishNotification.objects.filter(
                recipient=profile,
                is_read=False,
            ).update(is_read=True)
        return Response({'detail': 'Notifications marquées comme lues.'})


class ParishNotificationReadAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, notification_id):
        profile = UserProfile.objects.filter(user=request.user).first()
        updated = ParishNotification.objects.filter(
            pk=notification_id,
            recipient=profile,
            is_read=False,
        ).update(is_read=True)
        if not updated:
            return Response({'detail': 'Notification introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'detail': 'Notification marquée comme lue.'})


class MassScheduleAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        schedules = MassSchedule.objects.filter(active=True).filter(
            models.Q(date__isnull=True) | models.Q(date__gte=timezone.localdate())
        )
        return Response(MassScheduleSerializer(schedules, many=True).data)


class DonationsAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        donation_settings = DonationSettings.objects.filter(pk=1).first()
        return Response({
            'wave_identifier': donation_settings.wave_identifier if donation_settings else '',
            'orange_money_identifier': donation_settings.orange_money_identifier if donation_settings else '',
            'instructions': donation_settings.instructions if donation_settings else '',
        })


class MessagingContactsAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profiles = UserProfile.objects.select_related('group').prefetch_related('parish_entities').filter(
            otp_verified=True,
        ).exclude(user=request.user)
        query = request.query_params.get('q', '').strip()
        if query:
            profiles = profiles.filter(
                Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
                | Q(group__name__icontains=query)
                | Q(parish_entities__name__icontains=query)
            ).distinct()
        return Response(MessagingProfileSerializer(profiles.order_by('first_name', 'last_name')[:50], many=True).data)


class PrivateMessagesAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request):
        profile = UserProfile.objects.get(user=request.user)
        messages = PrivateMessage.objects.filter(Q(sender=profile) | Q(recipient=profile)).select_related(
            'sender__user', 'sender__group', 'recipient__user', 'recipient__group'
        )
        contact_id = request.query_params.get('contact_id')
        if contact_id is not None:
            try:
                contact_id = int(contact_id)
            except ValueError:
                return Response(
                    {'contact_id': 'L’identifiant du contact doit être un nombre.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            messages = messages.filter(
                Q(sender=profile, recipient_id=contact_id)
                | Q(recipient=profile, sender_id=contact_id)
            )
            if request.query_params.get('mark_read') != 'false':
                PrivateMessage.objects.filter(
                    sender_id=contact_id,
                    recipient=profile,
                    is_read=False,
                ).update(is_read=True)
        return Response(PrivateMessageSerializer(messages, many=True).data)

    @idempotent
    def post(self, request):
        profile = UserProfile.objects.get(user=request.user)
        serializer = PrivateMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        recipient = serializer.validated_data['recipient']
        if recipient == profile:
            return Response({'detail': 'Vous ne pouvez pas vous envoyer un message.'}, status=status.HTTP_400_BAD_REQUEST)
        audio = serializer.validated_data.get('audio')
        message = PrivateMessage.objects.create(
            sender=profile,
            recipient=recipient,
            body=serializer.validated_data.get('body', '').strip(),
            audio=audio,
        )
        return Response(PrivateMessageSerializer(message).data, status=status.HTTP_201_CREATED)


class PrivateMessageAudioAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, message_id):
        profile = UserProfile.objects.filter(user=request.user).first()
        message = PrivateMessage.objects.filter(
            pk=message_id,
            audio__isnull=False,
        ).filter(Q(sender=profile) | Q(recipient=profile)).first()
        if message is None or not message.audio:
            raise Http404
        response = FileResponse(
            message.audio.open('rb'),
            content_type=mimetypes.guess_type(message.audio.name)[0] or 'application/octet-stream',
        )
        response['Cache-Control'] = 'private, no-store'
        response['X-Content-Type-Options'] = 'nosniff'
        return response


class ParishEntitiesAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = UserProfile.objects.get(user=request.user)
        entities = NotificationGroup.objects.order_by('name')
        return Response(NotificationGroupSerializer(entities, many=True).data)


class ParishGroupMessagesAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request):
        profile = UserProfile.objects.get(user=request.user)
        member_entity_ids = set(profile.parish_entities.values_list('id', flat=True))
        if profile.group_id:
            member_entity_ids.add(profile.group_id)
        requested_values = (
            request.query_params.getlist('entity_ids')
            + request.query_params.getlist('entity_ids[]')
        )
        requested_entity_ids = set()
        if requested_values:
            try:
                requested_entity_ids = {
                    int(entity_id)
                    for value in requested_values
                    for entity_id in value.split(',')
                    if entity_id
                }
            except ValueError:
                return Response(
                    {'entity_ids': 'Les identifiants d’entités doivent être des nombres.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            visible_entity_ids = member_entity_ids.intersection(requested_entity_ids)
            if visible_entity_ids and request.query_params.get('mark_read') != 'false':
                now = timezone.now()
                for entity_id in visible_entity_ids:
                    ParishGroupReadState.objects.update_or_create(
                        profile=profile,
                        entity_id=entity_id,
                        defaults={'last_read_at': now},
                    )
        else:
            visible_entity_ids = member_entity_ids

        messages = ParishGroupMessage.objects.filter(
            entity_id__in=visible_entity_ids
        ).select_related('entity', 'sender__group').prefetch_related(
            'sender__parish_entities'
        )[:100]
        return Response(ParishGroupMessageSerializer(messages, many=True).data)

    @idempotent
    def post(self, request):
        profile = UserProfile.objects.get(user=request.user)
        serializer = ParishGroupMessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        audio = serializer.validated_data.get('audio')
        body = serializer.validated_data['body']
        with transaction.atomic():
            if audio:
                audio_content = audio.read()
                messages = [
                    ParishGroupMessage.objects.create(
                        entity=entity,
                        sender=profile,
                        body=body,
                        audio=ContentFile(audio_content, name=audio.name),
                    )
                    for entity in serializer.validated_data['entities']
                ]
            else:
                messages = ParishGroupMessage.objects.bulk_create(
                    [
                        ParishGroupMessage(entity=entity, sender=profile, body=body)
                        for entity in serializer.validated_data['entities']
                    ]
                )
        return Response(
            ParishGroupMessageSerializer(messages, many=True).data,
            status=status.HTTP_201_CREATED,
        )


class ParishGroupMessageAudioAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, message_id):
        profile = UserProfile.objects.filter(user=request.user).first()
        if profile is None:
            raise Http404
        message = ParishGroupMessage.objects.filter(pk=message_id, audio__isnull=False).select_related(
            'entity'
        ).first()
        if message is None or not message.audio:
            raise Http404
        member_entity_ids = set(profile.parish_entities.values_list('id', flat=True))
        if profile.group_id:
            member_entity_ids.add(profile.group_id)
        if message.entity_id not in member_entity_ids:
            raise Http404
        response = FileResponse(
            message.audio.open('rb'),
            content_type=mimetypes.guess_type(message.audio.name)[0] or 'application/octet-stream',
        )
        response['Cache-Control'] = 'private, no-store'
        response['X-Content-Type-Options'] = 'nosniff'
        return response


class MessagingUnreadAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = UserProfile.objects.get(user=request.user)
        private_count = PrivateMessage.objects.filter(
            recipient=profile,
            is_read=False,
        ).count()
        unread_private_messages = (
            PrivateMessage.objects.filter(recipient=profile, is_read=False)
            .select_related('sender')
            .order_by('-created_at')
        )
        unread_private_conversations = {}
        for message in unread_private_messages:
            conversation = unread_private_conversations.get(message.sender_id)
            if conversation is None:
                conversation = {
                    'profile_id': message.sender_id,
                    'sender_name': f'{message.sender.first_name} {message.sender.last_name}'.strip(),
                    'message_count': 0,
                    'body': message.body,
                    'created_at': message.created_at,
                }
                unread_private_conversations[message.sender_id] = conversation
            conversation['message_count'] += 1

        member_entity_ids = set(profile.parish_entities.values_list('id', flat=True))
        if profile.group_id:
            member_entity_ids.add(profile.group_id)
        now = timezone.now()
        ParishGroupReadState.objects.bulk_create(
            [
                ParishGroupReadState(
                    profile=profile,
                    entity_id=entity_id,
                    last_read_at=now,
                )
                for entity_id in member_entity_ids
            ],
            ignore_conflicts=True,
        )
        read_states = {
            state.entity_id: state.last_read_at
            for state in ParishGroupReadState.objects.filter(
                profile=profile,
                entity_id__in=member_entity_ids,
            )
        }
        unread_entities = []
        entity_count = 0
        for entity in NotificationGroup.objects.filter(id__in=member_entity_ids).order_by('name'):
            last_read_at = read_states.get(entity.id)
            unread_query = ParishGroupMessage.objects.filter(
                entity=entity,
            ).exclude(sender=profile)
            if last_read_at:
                unread_query = unread_query.filter(created_at__gt=last_read_at)
            else:
                unread_query = unread_query.none()
            message_count = unread_query.count()
            if message_count:
                entity_count += message_count
                latest_message = unread_query.select_related('sender').first()
                unread_entities.append({
                    'entity_id': entity.id,
                    'entity_name': entity.name,
                    'message_count': message_count,
                    'sender_name': f'{latest_message.sender.first_name} {latest_message.sender.last_name}'.strip(),
                    'body': latest_message.body,
                    'created_at': latest_message.created_at,
                })

        return Response({
            'private_count': private_count,
            'unread_private_conversations': list(unread_private_conversations.values()),
            'entity_count': entity_count,
            'total_count': private_count + entity_count,
            'unread_entities': unread_entities,
        })
