import os
import tempfile
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile
from io import BytesIO

from django.contrib.auth.models import User
from django.contrib.auth.models import Group, Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpResponse
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from backend.cors import DevelopmentCorsMiddleware

from .models import (
    Announcement,
    AnnouncementComment,
    AnnouncementLike,
    AnnouncementShare,
    DonationSettings,
    LiturgicalReading,
    MassSchedule,
    MassRequest,
    NotificationGroup,
    ParishNotification,
    OTPRequest,
    ParishGroupMessage,
    ParishDocument,
    ParishDocumentTemplate,
    ParishDocumentWorkflowEvent,
    PrivateMessage,
    ParishGroupReadState,
    OfflineQuizResult,
    QuizChallenge,
    QuizChallengeNotification,
    QuizChallengeParticipant,
    QuizQuestion,
    QuizSession,
    QuizSessionQuestion,
    UserProfile,
)


class DevelopmentCorsTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = DevelopmentCorsMiddleware(lambda request: HttpResponse(status=200))

    def test_allows_current_private_lan_origin(self):
        request = self.factory.options(
            '/api/',
            HTTP_ORIGIN='http://192.168.0.104:8083',
        )

        response = self.middleware(request)

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response['Access-Control-Allow-Origin'], 'http://192.168.0.104:8083')

    def test_rejects_public_or_unexpected_origins(self):
        for origin in ('http://example.com:8083', 'http://192.168.0.104:9000', 'https://192.168.0.104:8083'):
            with self.subTest(origin=origin):
                request = self.factory.options('/api/', HTTP_ORIGIN=origin)

                response = self.middleware(request)

                self.assertEqual(response.status_code, 200)
                self.assertNotIn('Access-Control-Allow-Origin', response)

    def test_allows_explicitly_configured_https_origin(self):
        with patch.dict(os.environ, {'DJANGO_CORS_ALLOWED_ORIGINS': 'https://paroisse.example.org'}):
            middleware = DevelopmentCorsMiddleware(lambda request: HttpResponse(status=200))
            request = self.factory.options(
                '/api/',
                HTTP_ORIGIN='https://paroisse.example.org',
            )

            response = middleware(request)

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response['Access-Control-Allow-Origin'], 'https://paroisse.example.org')


class NotificationGroupOrderingTests(TestCase):
    def test_group_list_is_sorted_alphabetically(self):
        NotificationGroup.objects.create(name='Zulu test')
        NotificationGroup.objects.create(name='alpha test')
        NotificationGroup.objects.create(name='Beta test')

        response = APIClient().get('/api/groupes/')

        self.assertEqual(response.status_code, 200)
        names = [group['name'] for group in response.json()]
        positions = [names.index(name) for name in ('alpha test', 'Beta test', 'Zulu test')]
        self.assertEqual(positions, sorted(positions))


class SegmentedAnnouncementsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.group_a = NotificationGroup.objects.create(name='Groupe A')
        self.group_b = NotificationGroup.objects.create(name='Groupe B')

        self.user = User.objects.create_user(username='+221771000001', password='demo123')
        self.profile = UserProfile.objects.create(
            user=self.user,
            phone_number=self.user.username,
            first_name='Amadou',
            last_name='Diop',
            group=self.group_a,
            otp_verified=True,
        )
        self.token, _ = Token.objects.get_or_create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

        self.general_announcement = Announcement.objects.create(
            title='Annonce générale',
            body='Visible pour tout le monde.',
            announcement_type='communique',
            published_at=timezone.now(),
        )
        self.group_a_announcement = Announcement.objects.create(
            title='Annonce groupe A',
            body='Visible pour le groupe A.',
            announcement_type='communique',
            published_at=timezone.now(),
        )
        self.group_a_announcement.target_groups.add(self.group_a)

        self.group_b_announcement = Announcement.objects.create(
            title='Annonce groupe B',
            body='Visible pour le groupe B.',
            announcement_type='communique',
            published_at=timezone.now(),
        )
        self.group_b_announcement.target_groups.add(self.group_b)

    def test_user_only_sees_general_and_matching_group_announcements(self):
        response = self.client.get('/api/annonces/')

        self.assertEqual(response.status_code, 200)
        ids = [item['id'] for item in response.json()]
        self.assertIn(self.general_announcement.id, ids)
        self.assertIn(self.group_a_announcement.id, ids)
        self.assertNotIn(self.group_b_announcement.id, ids)

    def test_user_sees_announcements_for_each_parish_entity_membership(self):
        self.profile.parish_entities.add(self.group_b)

        response = self.client.get('/api/annonces/')

        self.assertEqual(response.status_code, 200)
        ids = [item['id'] for item in response.json()]
        self.assertIn(self.group_a_announcement.id, ids)
        self.assertIn(self.group_b_announcement.id, ids)

    def test_announcement_feed_sorts_newest_publications_first(self):
        newest = Announcement.objects.create(
            title='Publication la plus récente',
            body='Contenu récent.',
            announcement_type='communique',
            published_at=timezone.now() + timedelta(minutes=1),
        )

        response = self.client.get('/api/annonces/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]['id'], newest.id)

    def test_paginated_home_feed_loads_all_visible_announcements_in_order(self):
        extra_announcements = [
            Announcement.objects.create(
                title=f'Publication supplémentaire {index}',
                body='Publication paginée.',
                announcement_type='communique',
                published_at=timezone.now() + timedelta(minutes=index + 2),
            )
            for index in range(9)
        ]

        first_page = self.client.get('/api/annonces/fil/')
        self.assertEqual(first_page.status_code, 200)
        self.assertEqual(len(first_page.json()['results']), 8)
        self.assertIsNotNone(first_page.json()['next'])
        self.assertNotIn(self.group_b_announcement.id, {
            item['id'] for item in first_page.json()['results']
        })

        second_page = self.client.get(first_page.json()['next'])
        self.assertEqual(second_page.status_code, 200)
        self.assertIsNone(second_page.json()['next'])
        visible_ids = {
            item['id']
            for item in first_page.json()['results'] + second_page.json()['results']
        }
        self.assertEqual(
            visible_ids,
            {
                self.general_announcement.id,
                self.group_a_announcement.id,
                *(item.id for item in extra_announcements),
            },
        )

    def test_global_search_returns_visible_content_and_verified_parishioners_only(self):
        self.general_announcement.title = 'Rencontre de prière'
        self.general_announcement.link_url = 'https://paroisse.example.org/rencontre'
        self.general_announcement.link_title = 'Page de la rencontre'
        self.general_announcement.save(update_fields=['title', 'link_url', 'link_title'])
        self.group_b_announcement.title = 'Rencontre privée'
        self.group_b_announcement.save(update_fields=['title'])
        LiturgicalReading.objects.create(
            date=timezone.localdate(),
            title='Prière du matin',
            content='Rencontre et prière.',
        )
        question = QuizQuestion.objects.create(
            testament='nouveau',
            category='Rencontre',
            prompt='Qui a participé à cette rencontre biblique ?',
            options=['Anne', 'Paul', 'Jean'],
            correct_option=1,
            explanation='La réponse est Paul.',
        )
        other_user = User.objects.create_user(username='+221771000009', password='demo123')
        other_profile = UserProfile.objects.create(
            user=other_user,
            phone_number='+221771000009',
            first_name='Rencontre',
            last_name='Paroissien',
            group=self.group_a,
            otp_verified=True,
        )

        response = self.client.get('/api/recherche/', {'q': 'rencontre'})

        self.assertEqual(response.status_code, 200)
        results = response.json()
        announcement = next(item for item in results if item['kind'] == 'announcement')
        self.assertEqual(announcement['announcement']['link_title'], 'Page de la rencontre')
        self.assertNotIn(self.group_b_announcement.id, [
            int(item['id']) for item in results if item['kind'] == 'announcement'
        ])
        self.assertTrue(any(item['kind'] == 'reading' for item in results))
        question_result = next(
            item for item in results
            if item['kind'] == 'question' and item['id'] == str(question.id)
        )
        self.assertEqual(question_result['id'], str(question.id))
        self.assertNotIn('options', question_result)
        self.assertNotIn('correct_option', question_result)
        parishioner_result = next(item for item in results if item['kind'] == 'parishioner')
        self.assertEqual(parishioner_result['profile_id'], other_profile.id)
        self.assertNotIn('phone_number', parishioner_result)

    def test_global_search_requires_authentication_and_minimum_query_length(self):
        anonymous = APIClient()
        self.assertEqual(anonymous.get('/api/recherche/', {'q': 'prière'}).status_code, 401)
        self.assertEqual(self.client.get('/api/recherche/', {'q': 'a'}).status_code, 400)
        self.assertEqual(self.client.get('/api/recherche/', {'q': 'a' * 101}).status_code, 400)

    def test_only_authenticated_parishioners_can_comment(self):
        anonymous_client = APIClient()
        url = f'/api/annonces/{self.general_announcement.id}/commentaires/'

        response = anonymous_client.post(url, {'body': 'Merci pour cette annonce.'}, format='json')

        self.assertEqual(response.status_code, 401)
        self.assertEqual(AnnouncementComment.objects.count(), 0)

    def test_authenticated_parishioner_can_create_and_read_comments(self):
        url = f'/api/annonces/{self.general_announcement.id}/commentaires/'

        response = self.client.post(url, {'body': 'Merci pour cette annonce.'}, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['author_name'], 'Amadou Diop')
        self.assertEqual(AnnouncementComment.objects.get().author, self.profile)

        comments_response = self.client.get(url)

        self.assertEqual(comments_response.status_code, 200)
        self.assertEqual(comments_response.json()[0]['body'], 'Merci pour cette annonce.')

    def test_announcement_feed_includes_comment_like_share_counts_and_user_like_state(self):
        AnnouncementComment.objects.create(
            announcement=self.general_announcement,
            author=self.profile,
            body='Un commentaire.',
        )
        AnnouncementLike.objects.create(
            announcement=self.general_announcement,
            user_profile=self.profile,
        )
        AnnouncementShare.objects.create(
            announcement=self.general_announcement,
            user_profile=self.profile,
        )

        response = self.client.get('/api/annonces/')

        self.assertEqual(response.status_code, 200)
        announcement = next(
            item for item in response.json()
            if item['id'] == self.general_announcement.id
        )
        self.assertEqual(announcement['comments_count'], 1)
        self.assertEqual(announcement['likes_count'], 1)
        self.assertEqual(announcement['shares_count'], 1)
        self.assertTrue(announcement['is_liked'])

    def test_anonymous_announcement_feed_includes_counts_and_unliked_state(self):
        AnnouncementComment.objects.create(
            announcement=self.general_announcement,
            author=self.profile,
            body='Un commentaire public.',
        )
        anonymous_client = APIClient()

        response = anonymous_client.get('/api/annonces/')

        self.assertEqual(response.status_code, 200)
        announcement = next(
            item for item in response.json()
            if item['id'] == self.general_announcement.id
        )
        self.assertEqual(announcement['comments_count'], 1)
        self.assertEqual(announcement['likes_count'], 0)
        self.assertEqual(announcement['shares_count'], 0)
        self.assertFalse(announcement['is_liked'])

    def test_parishioner_can_toggle_a_like_without_creating_duplicates(self):
        url = f'/api/annonces/{self.general_announcement.id}/j-aime/'

        liked_response = self.client.post(url, {}, format='json')
        self.assertEqual(liked_response.status_code, 200)
        self.assertEqual(liked_response.json(), {'is_liked': True, 'likes_count': 1})
        self.assertEqual(AnnouncementLike.objects.count(), 1)

        unliked_response = self.client.post(url, {}, format='json')
        self.assertEqual(unliked_response.status_code, 200)
        self.assertEqual(unliked_response.json(), {'is_liked': False, 'likes_count': 0})
        self.assertEqual(AnnouncementLike.objects.count(), 0)

    def test_explicit_like_state_is_safe_to_replay(self):
        url = f'/api/annonces/{self.general_announcement.id}/j-aime/'

        first = self.client.post(url, {'is_liked': True}, format='json')
        replay = self.client.post(url, {'is_liked': True}, format='json')
        self.assertEqual(first.status_code, 200)
        self.assertEqual(replay.status_code, 200)
        self.assertEqual(first.json(), {'is_liked': True, 'likes_count': 1})
        self.assertEqual(replay.json(), first.json())
        self.assertEqual(AnnouncementLike.objects.count(), 1)

        remove = self.client.post(url, {'is_liked': False}, format='json')
        repeated_remove = self.client.post(url, {'is_liked': False}, format='json')
        self.assertEqual(remove.json(), {'is_liked': False, 'likes_count': 0})
        self.assertEqual(repeated_remove.json(), remove.json())
        self.assertEqual(AnnouncementLike.objects.count(), 0)

        invalid = self.client.post(url, {'is_liked': 'yes'}, format='json')
        self.assertEqual(invalid.status_code, 400)

    def test_parishioner_can_record_a_share_and_anonymous_users_cannot(self):
        url = f'/api/annonces/{self.general_announcement.id}/partager/'

        response = self.client.post(url, {}, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json(), {'shares_count': 1})
        self.assertEqual(AnnouncementShare.objects.get().user_profile, self.profile)

        anonymous_response = APIClient().post(url, {}, format='json')
        self.assertEqual(anonymous_response.status_code, 401)
        self.assertEqual(AnnouncementShare.objects.count(), 1)

    def test_comments_require_a_profile_and_non_empty_content(self):
        user_without_profile = User.objects.create_user(
            username='+221771000099',
            password='demo123',
        )
        token, _ = Token.objects.get_or_create(user=user_without_profile)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        url = f'/api/annonces/{self.general_announcement.id}/commentaires/'

        no_profile_response = client.post(url, {'body': 'Commentaire'}, format='json')
        self.assertEqual(no_profile_response.status_code, 403)
        like_response = client.post(
            f'/api/annonces/{self.general_announcement.id}/j-aime/',
            {},
            format='json',
        )
        self.assertEqual(like_response.status_code, 403)
        self.assertIn('detail', like_response.json())
        share_response = client.post(
            f'/api/annonces/{self.general_announcement.id}/partager/',
            {},
            format='json',
        )
        self.assertEqual(share_response.status_code, 403)
        self.assertIn('detail', share_response.json())

        empty_response = self.client.post(url, {'body': '   '}, format='json')
        self.assertEqual(empty_response.status_code, 400)
        self.assertEqual(AnnouncementComment.objects.count(), 0)

    def test_comment_access_respects_announcement_group_visibility(self):
        url = f'/api/annonces/{self.group_b_announcement.id}/commentaires/'

        response = self.client.post(url, {'body': 'Commentaire non autorisé.'}, format='json')

        self.assertEqual(response.status_code, 404)
        self.assertEqual(AnnouncementComment.objects.count(), 0)

    def test_announcement_video_url_is_returned_to_mobile_clients(self):
        self.general_announcement.video_url = 'https://media.example.org/paroisse.mp4'
        self.general_announcement.save(update_fields=['video_url'])

        response = self.client.get('/api/annonces/')

        self.assertEqual(response.status_code, 200)
        announcement = next(item for item in response.json() if item['id'] == self.general_announcement.id)
        self.assertEqual(announcement['video_url'], 'https://media.example.org/paroisse.mp4')
        self.assertEqual(announcement['media_url'], 'https://media.example.org/paroisse.mp4')
        self.assertEqual(announcement['media_type'], 'video')

    def test_uploaded_announcement_video_is_returned_as_absolute_url(self):
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                self.general_announcement.media_file = SimpleUploadedFile(
                    'paroisse.mp4',
                    b'video content',
                    content_type='video/mp4',
                )
                self.general_announcement.save(update_fields=['media_file'])

                response = self.client.get('/api/annonces/')

                self.assertEqual(response.status_code, 200)
                announcement = next(item for item in response.json() if item['id'] == self.general_announcement.id)
                self.assertTrue(announcement['media_url'].startswith(
                    'http://testserver/media/announcements/media/'
                ))
                self.assertEqual(announcement['video_url'], announcement['media_url'])
                self.assertEqual(announcement['media_type'], 'video')

    def test_uploaded_announcement_image_is_returned_as_image_media(self):
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                self.general_announcement.media_file = SimpleUploadedFile(
                    'paroisse.png',
                    b'image content',
                    content_type='image/png',
                )
                self.general_announcement.save(update_fields=['media_file'])

                response = self.client.get('/api/annonces/')

                self.assertEqual(response.status_code, 200)
                announcement = next(item for item in response.json() if item['id'] == self.general_announcement.id)
                self.assertTrue(announcement['media_url'].startswith(
                    'http://testserver/media/announcements/media/'
                ))
                self.assertEqual(announcement['media_type'], 'image')
                self.assertEqual(announcement['video_url'], '')


class MassRequestTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        user = User.objects.create_user(username='+221771000010', password='demo123')
        self.profile = UserProfile.objects.create(
            user=user,
            phone_number=user.username,
            first_name='Aminata',
            last_name='Fall',
            otp_verified=True,
        )
        token, _ = Token.objects.get_or_create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def test_create_mass_request_with_date_and_time(self):
        response = self.client.post('/api/demandes-messe/', {
            'phone': '+221771000010',
            'locality': 'Dakar, Yoff',
            'preferred_date': '2026-09-15T16:30:00Z',
            'message': 'Messe pour une intention familiale.',
        }, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['preferred_date'], '2026-09-15T16:30:00Z')
        self.assertEqual(response.json()['locality'], 'Dakar, Yoff')
        self.assertEqual(MassRequest.objects.count(), 1)

    def test_ouakam_residents_receive_personalized_parish_contact_without_creating_request(self):
        response = self.client.post('/api/demandes-messe/', {
            'phone': '+221771000010',
            'locality': 'Ouakam, Cité Asecna',
            'message': 'Messe pour une intention familiale.',
        }, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['blocked'])
        self.assertIn('Aminata Fall', response.json()['detail'])
        self.assertIn('77 123 45 67', response.json()['detail'])
        self.assertEqual(MassRequest.objects.count(), 0)

    def test_phone_is_required_and_cannot_be_blank(self):
        for payload in (
            {'locality': 'Dakar', 'message': 'Intention de messe.'},
            {'phone': '', 'locality': 'Dakar', 'message': 'Intention de messe.'},
            {'phone': '   ', 'locality': 'Dakar', 'message': 'Intention de messe.'},
        ):
            with self.subTest(payload=payload):
                response = self.client.post('/api/demandes-messe/', payload, format='json')
                self.assertEqual(response.status_code, 400)
        self.assertEqual(MassRequest.objects.count(), 0)

    def test_locality_is_required(self):
        response = self.client.post('/api/demandes-messe/', {
            'phone': '+221771000010',
            'message': 'Intention de messe.',
        }, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(MassRequest.objects.count(), 0)

    def test_mass_request_status_change_creates_an_unread_private_notification(self):
        mass_request = MassRequest.objects.create(
            requester=self.profile,
            phone='+221771000010',
            locality='Dakar, Yoff',
            message='Intention de messe.',
        )
        self.assertFalse(ParishNotification.objects.exists())

        mass_request.status = 'accepted'
        mass_request.save(update_fields=['status'])

        response = self.client.get('/api/notifications/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        notification = response.json()[0]
        self.assertEqual(notification['kind'], 'mass_request_status')
        self.assertIn('acceptée', notification['message'])
        self.assertEqual(notification['mass_request_id'], mass_request.id)

        read_response = self.client.post(f"/api/notifications/{notification['id']}/read/", {}, format='json')
        self.assertEqual(read_response.status_code, 200)
        self.assertEqual(self.client.get('/api/notifications/').json(), [])

    def test_mark_all_parish_notifications_read_does_not_change_messages(self):
        sender = User.objects.create_user(username='+221771000011', password='demo123')
        sender_profile = UserProfile.objects.create(
            user=sender,
            phone_number=sender.username,
            first_name='Moussa',
            last_name='Ba',
            otp_verified=True,
        )
        private_message = PrivateMessage.objects.create(
            sender=sender_profile,
            recipient=self.profile,
            body='Message à garder non lu.',
        )
        mass_request = MassRequest.objects.create(
            requester=self.profile,
            phone='+221771000010',
            locality='Dakar, Yoff',
            message='Intention de messe.',
        )
        mass_request.status = 'declined'
        mass_request.save(update_fields=['status'])

        response = self.client.post('/api/notifications/read/', {}, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertFalse(ParishNotification.objects.filter(is_read=False).exists())
        private_message.refresh_from_db()
        self.assertFalse(private_message.is_read)
        self.assertEqual(self.client.get('/api/messagerie/non-lus/').json()['total_count'], 1)

    def test_parish_notification_is_visible_only_to_its_recipient(self):
        other_user = User.objects.create_user(username='+221771000012', password='demo123')
        other_profile = UserProfile.objects.create(
            user=other_user,
            phone_number=other_user.username,
            first_name='Moussa',
            last_name='Ba',
            otp_verified=True,
        )
        notification = ParishNotification.objects.create(
            recipient=other_profile,
            kind='mass_request_status',
            title='Réponse',
            message='Demande acceptée.',
        )

        self.assertEqual(self.client.get('/api/notifications/').json(), [])
        response = self.client.post(f'/api/notifications/{notification.id}/read/', {}, format='json')

        self.assertEqual(response.status_code, 404)
        notification.refresh_from_db()
        self.assertFalse(notification.is_read)


class PasswordResetTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.client = APIClient()
        self.user = User.objects.create_user(username='+221771000030', password='ancien123')
        self.profile = UserProfile.objects.create(
            user=self.user,
            phone_number=self.user.username,
            first_name='Aminata',
            last_name='Fall',
            otp_verified=True,
        )
        self.token, _ = Token.objects.get_or_create(user=self.user)

    @override_settings(DEBUG=True, OTP_PROVIDER='console')
    def test_password_reset_requires_a_fresh_single_use_code_and_revokes_old_token(self):
        request = self.client.post('/api/auth/password-reset/request/', {
            'phone_number': self.user.username,
        }, format='json')
        code = request.json()['otp_code']

        response = self.client.post('/api/auth/password-reset/confirm/', {
            'phone_number': self.user.username,
            'otp_code': code,
            'new_password': 'nouveau123',
        }, format='json')

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('nouveau123'))
        self.assertFalse(Token.objects.filter(key=self.token.key).exists())
        self.assertTrue(OTPRequest.objects.get(code=code).used)

        reuse = self.client.post('/api/auth/password-reset/confirm/', {
            'phone_number': self.user.username,
            'otp_code': code,
            'new_password': 'autre123',
        }, format='json')
        self.assertEqual(reuse.status_code, 400)

    @override_settings(DEBUG=True, OTP_PROVIDER='console')
    def test_password_reset_does_not_issue_codes_for_unverified_numbers(self):
        self.profile.otp_verified = False
        self.profile.save(update_fields=['otp_verified'])

        response = self.client.post('/api/auth/password-reset/request/', {
            'phone_number': self.user.username,
        }, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('otp_code', response.json())
        self.assertFalse(OTPRequest.objects.filter(purpose='password_reset').exists())

    @override_settings(DEBUG=True, OTP_PROVIDER='console')
    def test_requesting_a_new_code_invalidates_the_previous_one(self):
        first_code = self.client.post('/api/auth/password-reset/request/', {
            'phone_number': self.user.username,
        }, format='json').json()['otp_code']
        self.client.post('/api/auth/password-reset/request/', {
            'phone_number': self.user.username,
        }, format='json')

        response = self.client.post('/api/auth/password-reset/confirm/', {
            'phone_number': self.user.username,
            'otp_code': first_code,
            'new_password': 'nouveau123',
        }, format='json')

        self.assertEqual(response.status_code, 400)

    @override_settings(
        DEBUG=False,
        OTP_PROVIDER='console',
        WHATSAPP_ACCESS_TOKEN='',
        WHATSAPP_PHONE_NUMBER_ID='',
        WHATSAPP_GRAPH_API_VERSION='',
        WHATSAPP_OTP_TEMPLATE_NAME='',
    )
    def test_password_reset_fails_closed_without_a_real_sms_provider(self):
        response = self.client.post('/api/auth/password-reset/request/', {
            'phone_number': self.user.username,
        }, format='json')

        self.assertEqual(response.status_code, 503)
        self.assertNotIn('otp_code', response.json())

    @override_settings(
        DEBUG=False,
        OTP_PROVIDER='whatsapp',
        WHATSAPP_ACCESS_TOKEN='test-token',
        WHATSAPP_PHONE_NUMBER_ID='123456',
        WHATSAPP_GRAPH_API_VERSION='v22.0',
        WHATSAPP_OTP_TEMPLATE_NAME='account_password_reset',
    )
    @patch('api.views.send_whatsapp_otp')
    def test_password_reset_sends_whatsapp_template_without_returning_the_code(self, send_otp):
        response = self.client.post('/api/auth/password-reset/request/', {
            'phone_number': self.user.username,
        }, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('otp_code', response.json())
        self.assertEqual(OTPRequest.objects.filter(purpose='password_reset').count(), 1)
        send_otp.assert_called_once()

    def test_registration_requires_at_least_one_parish_entity(self):
        response = self.client.post('/api/auth/register/', {
            'first_name': 'Awa',
            'last_name': 'Ndiaye',
            'phone_number': '+221770000099',
            'parish_entity_names': [],
            'password': 'secret123',
        }, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(username='+221770000099').exists())


class MassRequestPaymentInfoTests(TestCase):
    @override_settings(MASS_REQUEST_PAYMENT_PHONE='+221 77 123 45 67')
    def test_payment_phone_is_available_without_authentication(self):
        response = self.client.get('/api/demandes-messe/paiement/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            'payment_phone': '+221 77 123 45 67',
            'contact_phone': '77 123 45 67',
        })

    def test_parish_contact_phone_can_be_changed_in_admin_settings(self):
        DonationSettings.objects.create(parish_contact_phone='+221 76 555 12 34')

        response = self.client.get('/api/demandes-messe/paiement/')

        self.assertEqual(response.json()['contact_phone'], '+221 76 555 12 34')

    @override_settings(MASS_REQUEST_PAYMENT_PHONE='')
    def test_unconfigured_payment_phone_is_returned_as_empty(self):
        response = self.client.get('/api/demandes-messe/paiement/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            'payment_phone': '',
            'contact_phone': '77 123 45 67',
        })


class ParishServiceTests(TestCase):
    def test_mass_schedule_is_public_and_excludes_past_special_dates(self):
        today = timezone.localdate()
        MassSchedule.objects.create(
            weekday=today.weekday(),
            time='08:30',
            location='Église paroissiale',
        )
        MassSchedule.objects.create(
            date=today + timedelta(days=2),
            time='18:00',
            location='Chapelle',
        )
        MassSchedule.objects.create(
            date=today - timedelta(days=1),
            time='18:00',
            location='Ancienne date',
        )

        response = APIClient().get('/api/horaires-messes/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 2)
        self.assertEqual(
            {item['location'] for item in response.json()},
            {'Église paroissiale', 'Chapelle'},
        )

    def test_donation_settings_are_public_and_return_empty_when_unconfigured(self):
        client = APIClient()
        response = client.get('/api/dons/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            'wave_identifier': '',
            'orange_money_identifier': '',
            'instructions': '',
        })

        DonationSettings.objects.create(
            wave_identifier='Wave-123',
            orange_money_identifier='+221770000000',
            instructions='Indiquez le motif de votre don.',
        )
        configured = client.get('/api/dons/')
        self.assertEqual(configured.status_code, 200)
        self.assertEqual(configured.json()['wave_identifier'], 'Wave-123')
        self.assertEqual(configured.json()['orange_money_identifier'], '+221770000000')

    def test_staff_can_create_donation_settings_in_admin(self):
        admin_user = User.objects.create_superuser(
            username='donation-admin',
            email='donations@example.org',
            password='admin-password',
        )
        client = Client()
        client.force_login(admin_user)

        response = client.post(reverse('admin:api_donationsettings_add'), {
            'wave_identifier': 'Wave-123',
            'orange_money_identifier': '+221770000000',
            'instructions': 'Indiquez le motif de votre don.',
            '_save': 'Enregistrer',
        })

        self.assertEqual(response.status_code, 302)
        settings = DonationSettings.objects.get(pk=1)
        self.assertEqual(settings.wave_identifier, 'Wave-123')
        changelist = client.get(reverse('admin:api_donationsettings_changelist'))
        self.assertEqual(changelist.status_code, 200)

    def test_mass_schedule_admin_explains_when_weekday_and_date_are_both_set(self):
        admin_user = User.objects.create_superuser(
            username='schedule-admin',
            email='schedule@example.org',
            password='admin-password',
        )
        client = Client()
        client.force_login(admin_user)

        response = client.post(reverse('admin:api_massschedule_add'), {
            'weekday': '1',
            'date': '2026-11-10',
            'time': '06:30',
            'location': 'Église NDA',
            'active': 'on',
            '_save': 'Enregistrer',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Pour un horaire récurrent, effacez la date ponctuelle.')
        self.assertEqual(MassSchedule.objects.count(), 0)

    def test_staff_can_create_recurring_mass_schedule_in_admin(self):
        admin_user = User.objects.create_superuser(
            username='schedule-admin',
            email='schedule@example.org',
            password='admin-password',
        )
        client = Client()
        client.force_login(admin_user)

        response = client.post(reverse('admin:api_massschedule_add'), {
            'weekday': '0',
            'date': '',
            'time': '06:30',
            'location': 'Église NDA',
            'active': 'on',
            '_save': 'Enregistrer',
        })

        self.assertEqual(response.status_code, 302)
        schedule = MassSchedule.objects.get()
        self.assertEqual(schedule.weekday, 0)
        self.assertIsNone(schedule.date)


class ChurchManagementAdminActionsTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username='church-admin',
            email='admin@example.org',
            password='admin-password',
        )
        self.client = Client()
        self.client.force_login(self.admin_user)

    def test_admin_can_publish_and_unpublish_announcements(self):
        announcement = Announcement.objects.create(
            title='Messe paroissiale',
            body='Annonce à publier.',
            announcement_type='communique',
        )
        changelist_url = reverse('admin:api_announcement_changelist')

        response = self.client.post(changelist_url, {
            'action': 'publish_selected',
            '_selected_action': [announcement.pk],
            'index': '0',
        })

        self.assertEqual(response.status_code, 302)
        announcement.refresh_from_db()
        self.assertIsNotNone(announcement.published_at)

        response = self.client.post(changelist_url, {
            'action': 'unpublish_selected',
            '_selected_action': [announcement.pk],
            'index': '0',
        })

        self.assertEqual(response.status_code, 302)
        announcement.refresh_from_db()
        self.assertIsNone(announcement.published_at)

    def test_admin_can_accept_and_decline_mass_requests(self):
        mass_request = MassRequest.objects.create(message='Intention de prière.')
        changelist_url = reverse('admin:api_massrequest_changelist')

        response = self.client.post(changelist_url, {
            'action': 'accept_selected',
            '_selected_action': [mass_request.pk],
            'index': '0',
        })

        self.assertEqual(response.status_code, 302)
        mass_request.refresh_from_db()
        self.assertEqual(mass_request.status, 'accepted')

        response = self.client.post(changelist_url, {
            'action': 'decline_selected',
            '_selected_action': [mass_request.pk],
            'index': '0',
        })

        self.assertEqual(response.status_code, 302)
        mass_request.refresh_from_db()
        self.assertEqual(mass_request.status, 'declined')


class ParishDocumentAdminTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(
            username='parish-secretary',
            password='secretary-password',
            is_staff=True,
        )
        self.priest = User.objects.create_user(
            username='parish-priest',
            password='priest-password',
            is_staff=True,
        )
        self._grant_permissions(self.author, 'view_parishdocument', 'add_parishdocument', 'change_parishdocument')
        self._grant_permissions(
            self.priest,
            'view_parishdocument',
            'change_parishdocument',
            'view_sensitive_parishdocument',
            'approve_parishdocument',
        )
        template_permission = Permission.objects.get(
            content_type__app_label='api',
            content_type__model='parishdocumenttemplate',
            codename='view_parishdocumenttemplate',
        )
        self.author.user_permissions.add(template_permission)
        self.client = Client()
        self.changelist_url = reverse('admin:api_parishdocument_changelist')

    def _grant_permissions(self, user, *codenames):
        permissions = Permission.objects.filter(
            content_type__app_label='api',
            content_type__model='parishdocument',
            codename__in=codenames,
        )
        user.user_permissions.add(*permissions)

    def _run_action(self, user, document, action):
        self.client.force_login(user)
        return self.client.post(self.changelist_url, {
            'action': action,
            '_selected_action': [document.pk],
            'index': '0',
        })

    def test_confidential_category_is_restricted_and_hidden_from_ordinary_staff(self):
        document = ParishDocument.objects.create(
            title='Registre de baptême',
            category='sacraments',
            content='Données sensibles.',
        )
        self.assertEqual(document.confidentiality, 'restricted')
        sacramental_document = ParishDocument.objects.create(
            title='Extrait de baptême',
            category='pastoral',
            document_type='sacramental_record',
            confidentiality='internal',
        )
        self.assertEqual(sacramental_document.confidentiality, 'restricted')

        self.client.force_login(self.author)
        response = self.client.get(self.changelist_url)
        self.assertNotContains(response, 'Registre de baptême')
        hidden_document = self.client.get(
            reverse('admin:api_parishdocument_change', args=[document.pk])
        )
        self.assertRedirects(
            hidden_document,
            reverse('admin:index'),
            fetch_redirect_response=False,
        )

        self.client.force_login(self.priest)
        visible_document = self.client.get(
            reverse('admin:api_parishdocument_change', args=[document.pk])
        )
        self.assertEqual(visible_document.status_code, 200)

    def test_default_staff_groups_have_the_expected_workflow_permissions(self):
        secretariat = Group.objects.get(name='Secrétariat paroissial')
        priests = Group.objects.get(name='Prêtres')

        self.assertTrue(secretariat.permissions.filter(codename='view_parishdocument').exists())
        self.assertFalse(secretariat.permissions.filter(codename='approve_parishdocument').exists())
        self.assertTrue(priests.permissions.filter(codename='approve_parishdocument').exists())
        self.assertTrue(priests.permissions.filter(codename='view_sensitive_parishdocument').exists())
        self.assertEqual(
            Permission.objects.get(codename='approve_parishdocument').name,
            'Peut valider et archiver les documents paroissiaux',
        )

    def test_workflow_requires_separate_author_and_tracks_each_step(self):
        document = ParishDocument.objects.create(
            title='Courrier paroissial',
            category='administrative',
            content='Contenu à valider.',
            created_by=self.author,
        )

        response = self._run_action(self.author, document, 'submit_for_review')
        self.assertEqual(response.status_code, 302)
        document.refresh_from_db()
        self.assertEqual(document.status, 'review')

        response = self._run_action(self.author, document, 'approve_documents')
        self.assertEqual(response.status_code, 302)
        document.refresh_from_db()
        self.assertEqual(document.status, 'review')
        self.assertIsNone(document.approved_by)

        response = self._run_action(self.priest, document, 'approve_documents')
        self.assertEqual(response.status_code, 302)
        document.refresh_from_db()
        self.assertEqual(document.status, 'approved')
        self.assertEqual(document.approved_by, self.priest)
        self.assertIsNotNone(document.approved_at)

        response = self._run_action(self.priest, document, 'archive_documents')
        self.assertEqual(response.status_code, 302)
        document.refresh_from_db()
        self.assertEqual(document.status, 'archived')
        self.assertEqual(
            list(document.workflow_events.values_list('action', flat=True)),
            ['archived', 'approved', 'submitted'],
        )

    def test_empty_drafts_cannot_be_submitted_for_review(self):
        document = ParishDocument.objects.create(
            title='Brouillon vide',
            category='administrative',
            created_by=self.author,
        )

        response = self._run_action(self.author, document, 'submit_for_review')

        self.assertEqual(response.status_code, 302)
        document.refresh_from_db()
        self.assertEqual(document.status, 'draft')
        self.assertFalse(document.workflow_events.filter(action='submitted').exists())

    def test_admin_labels_and_forms_are_in_french(self):
        self.client.force_login(User.objects.create_superuser(
            username='admin-french',
            email='admin-french@example.org',
            password='admin-password',
        ))
        index_response = self.client.get(reverse('admin:index'))
        self.assertEqual(index_response.status_code, 200)
        self.assertContains(index_response, 'Paroisse NDA Ouakam')
        self.assertContains(index_response, 'Paroisse Notre Dame des Anges de Ouakam')
        self.assertContains(index_response, 'Gestion paroissiale')
        self.assertContains(index_response, 'parish-model-cards')
        self.assertContains(index_response, 'parish-model-card')
        self.assertContains(index_response, 'Documents paroissiaux')
        self.assertContains(index_response, 'Modèles de documents paroissiaux')
        self.assertContains(index_response, 'Nouveau document')
        self.assertContains(index_response, 'Demandes de messe')
        self.assertContains(index_response, 'Nouvelle annonce')

        form_response = self.client.get(reverse('admin:api_parishdocument_add'))
        self.assertEqual(form_response.status_code, 200)
        for french_label in ('Titre', 'Catégorie', 'Date du document', 'Contenu du document', 'Fichier à archiver'):
            with self.subTest(label=french_label):
                self.assertContains(form_response, french_label)
        self.assertNotContains(form_response, 'Created by')
        self.assertNotContains(form_response, 'Document date')

    def test_announcement_form_supports_video_url_and_media_upload(self):
        superuser = User.objects.create_superuser(
            username='announcement-admin',
            email='admin@example.org',
            password='admin-password',
        )
        self.client.force_login(superuser)
        response = self.client.get(reverse('admin:api_announcement_add'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Adresse de la vidéo')
        self.assertContains(response, 'Fichier média')
        self.assertContains(response, 'JPG, JPEG et PNG')

    def test_custom_admin_styles_load_after_django_list_and_responsive_styles(self):
        superuser = User.objects.create_superuser(
            username='announcement-style-admin',
            email='styles@example.org',
            password='admin-password',
        )
        self.client.force_login(superuser)
        response = self.client.get(reverse('admin:api_announcement_changelist'))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        custom_styles = content.index('/static/api/admin/parish-admin.css?v=7')
        responsive_styles = content.index('/static/admin/css/responsive.css')
        changelist_styles = content.index('/static/admin/css/changelists.css')
        self.assertGreater(custom_styles, responsive_styles)
        self.assertGreater(custom_styles, changelist_styles)
        self.assertIn('/static/api/admin/parish-admin.js', content)

    def test_all_admin_permission_labels_are_in_french(self):
        self.assertEqual(
            Permission.objects.get(
                content_type__app_label='auth',
                codename='add_user',
            ).name,
            'Peut ajouter un compte utilisateur',
        )
        self.assertEqual(
            Permission.objects.get(
                content_type__app_label='api',
                codename='change_announcement',
            ).name,
            'Peut modifier une annonce',
        )

    def test_word_export_is_generated_and_downloadable_from_admin(self):
        document = ParishDocument.objects.create(
            title='Compte rendu de réunion',
            category='pastoral',
            document_date='2026-10-16',
            reference_number='CR-2026-10',
            content='Première ligne.\nDeuxième ligne.',
        )
        self.client.force_login(self.author)

        response = self.client.get(
            reverse('admin:api_parishdocument_download_word', kwargs={'object_id': document.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        )
        self.assertIn('attachment;', response['Content-Disposition'])
        with ZipFile(BytesIO(response.content)) as archive:
            body = archive.read('word/document.xml').decode()
        self.assertIn('Compte rendu de réunion', body)
        self.assertIn('Première ligne.', body)
        self.assertIn('Deuxième ligne.', body)

    def test_reusable_template_prefills_a_new_daily_document(self):
        template = ParishDocumentTemplate.objects.create(
            name='Compte rendu standard',
            category='pastoral',
            document_type='minutes',
            title_template='Compte rendu — [date]',
            content_template='Présents :\nDécisions :\nActions à suivre :',
            created_by=self.author,
        )
        self.client.force_login(self.author)

        response = self.client.get(
            reverse(
                'admin:api_parishdocumenttemplate_create_document',
                kwargs={'object_id': template.pk},
            )
        )

        self.assertEqual(response.status_code, 302)
        add_response = self.client.get(response['Location'])
        self.assertEqual(add_response.status_code, 200)
        self.assertContains(add_response, 'Compte rendu — [date]')
        self.assertContains(add_response, 'Présents :')
        self.assertContains(add_response, 'Décisions :')

    def test_uploaded_archive_is_private_and_download_requires_permission(self):
        with tempfile.TemporaryDirectory() as private_root:
            with override_settings(PRIVATE_DOCUMENT_ROOT=private_root):
                document = ParishDocument.objects.create(
                    title='Courrier confidentiel',
                    category='finance',
                    attachment=SimpleUploadedFile('justificatif.pdf', b'%PDF-archive-data'),
                )
                self.assertTrue(document.attachment.path.startswith(private_root))
                self.assertNotIn('/media/', document.attachment.url)

                self.client.force_login(self.author)
                denied = self.client.get(document.attachment.url)
                self.assertEqual(denied.status_code, 404)

                self.client.force_login(self.priest)
                allowed = self.client.get(document.attachment.url)
                self.assertEqual(allowed.status_code, 200)
                self.assertEqual(b''.join(allowed.streaming_content), b'%PDF-archive-data')


class PrivateMessagingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sender = User.objects.create_user(username='+221771000020', password='demo123')
        self.recipient = User.objects.create_user(username='+221771000021', password='demo123')
        self.sender_profile = UserProfile.objects.create(
            user=self.sender, phone_number=self.sender.username, first_name='Awa', last_name='Diop', otp_verified=True
        )
        self.recipient_profile = UserProfile.objects.create(
            user=self.recipient, phone_number=self.recipient.username, first_name='Moussa', last_name='Fall', otp_verified=True
        )
        token, _ = Token.objects.get_or_create(user=self.sender)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def test_user_can_send_and_read_private_message(self):
        message_data = {
            'recipient_id': self.recipient_profile.id,
            'body': 'Paix et bénédiction à toi.',
        }
        response = self.client.post(
            '/api/messagerie/messages/',
            message_data,
            format='json',
            HTTP_IDEMPOTENCY_KEY='private-message-once',
        )
        replay = self.client.post(
            '/api/messagerie/messages/',
            message_data,
            format='json',
            HTTP_IDEMPOTENCY_KEY='private-message-once',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(replay.status_code, 201)
        self.assertEqual(response.json(), replay.json())
        self.assertEqual(PrivateMessage.objects.count(), 1)
        inbox_response = self.client.get('/api/messagerie/messages/')
        self.assertEqual(inbox_response.status_code, 200)
        self.assertEqual(inbox_response.json()[0]['body'], 'Paix et bénédiction à toi.')

    def test_private_voice_message_is_available_only_to_conversation_members(self):
        outsider = User.objects.create_user(username='+221771000025', password='demo123')
        UserProfile.objects.create(
            user=outsider,
            phone_number=outsider.username,
            first_name='Sali',
            last_name='Ndiaye',
            otp_verified=True,
        )
        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            response = self.client.post('/api/messagerie/messages/', {
                'recipient_id': self.recipient_profile.id,
                'audio': SimpleUploadedFile('vocal.webm', b'voice-data', content_type='audio/webm'),
            }, format='multipart')

            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.json()['body'], '')
            audio_path = f"/api{response.json()['audio_url']}"
            self.assertEqual(
                b''.join(self.client.get(audio_path).streaming_content),
                b'voice-data',
            )

            recipient_token, _ = Token.objects.get_or_create(user=self.recipient)
            recipient_client = APIClient()
            recipient_client.credentials(HTTP_AUTHORIZATION=f'Token {recipient_token.key}')
            self.assertEqual(recipient_client.get(audio_path).status_code, 200)

            outsider_token, _ = Token.objects.get_or_create(user=outsider)
            outsider_client = APIClient()
            outsider_client.credentials(HTTP_AUTHORIZATION=f'Token {outsider_token.key}')
            self.assertEqual(outsider_client.get(audio_path).status_code, 404)

    def test_parish_voice_message_is_available_only_to_entity_members(self):
        entity = NotificationGroup.objects.create(name='Chorale vocale')
        self.sender_profile.parish_entities.add(entity)
        self.recipient_profile.parish_entities.add(entity)
        outsider = User.objects.create_user(username='+221771000026', password='demo123')
        UserProfile.objects.create(
            user=outsider,
            phone_number=outsider.username,
            first_name='Sali',
            last_name='Ndiaye',
            otp_verified=True,
        )
        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            response = self.client.post('/api/messagerie/entites/messages/', {
                'entity_ids': [entity.id],
                'audio': SimpleUploadedFile('chorale.webm', b'group-voice', content_type='audio/webm'),
            }, format='multipart')

            self.assertEqual(response.status_code, 201)
            audio_path = f"/api{response.json()[0]['audio_url']}"
            self.assertEqual(
                b''.join(self.client.get(audio_path).streaming_content),
                b'group-voice',
            )

            recipient_token, _ = Token.objects.get_or_create(user=self.recipient)
            recipient_client = APIClient()
            recipient_client.credentials(HTTP_AUTHORIZATION=f'Token {recipient_token.key}')
            self.assertEqual(recipient_client.get(audio_path).status_code, 200)

            outsider_token, _ = Token.objects.get_or_create(user=outsider)
            outsider_client = APIClient()
            outsider_client.credentials(HTTP_AUTHORIZATION=f'Token {outsider_token.key}')
            self.assertEqual(outsider_client.get(audio_path).status_code, 404)

    def test_private_voice_upload_rejects_unsupported_types_and_files_over_limit(self):
        invalid_type = self.client.post('/api/messagerie/messages/', {
            'recipient_id': self.recipient_profile.id,
            'audio': SimpleUploadedFile('vocal.txt', b'voice-data', content_type='text/plain'),
        }, format='multipart')
        self.assertEqual(invalid_type.status_code, 400)

        oversized = self.client.post('/api/messagerie/messages/', {
            'recipient_id': self.recipient_profile.id,
            'audio': SimpleUploadedFile(
                'vocal.webm',
                b'x' * (8 * 1024 * 1024 + 1),
                content_type='audio/webm',
            ),
        }, format='multipart')
        self.assertEqual(oversized.status_code, 400)

    def test_unread_private_message_count_clears_only_after_opening_conversation(self):
        PrivateMessage.objects.create(
            sender=self.recipient_profile,
            recipient=self.sender_profile,
            body='Bonjour Awa.',
        )

        unread = self.client.get('/api/messagerie/non-lus/')
        self.assertEqual(unread.status_code, 200)
        self.assertEqual(unread.json()['private_count'], 1)
        self.assertEqual(unread.json()['total_count'], 1)
        self.assertEqual(
            unread.json()['unread_private_conversations'][0]['profile_id'],
            self.recipient_profile.id,
        )

        prefetch = self.client.get(
            '/api/messagerie/messages/',
            {'contact_id': self.recipient_profile.id, 'mark_read': 'false'},
        )
        self.assertEqual(prefetch.status_code, 200)
        self.assertEqual(self.client.get('/api/messagerie/non-lus/').json()['private_count'], 1)

        self.client.get('/api/messagerie/messages/')
        still_unread = self.client.get('/api/messagerie/non-lus/')
        self.assertEqual(still_unread.json()['private_count'], 1)

        conversation = self.client.get(
            '/api/messagerie/messages/',
            {'contact_id': self.recipient_profile.id},
        )
        self.assertEqual(conversation.status_code, 200)
        self.assertEqual(conversation.json()[0]['body'], 'Bonjour Awa.')
        read = self.client.get('/api/messagerie/non-lus/')
        self.assertEqual(read.json()['private_count'], 0)

    def test_private_messages_are_delivered_to_recipient_and_thread_is_isolated(self):
        response = self.client.post('/api/messagerie/messages/', {
            'recipient_id': self.recipient_profile.id,
            'body': 'Bonjour Moussa.',
        }, format='json')
        self.assertEqual(response.status_code, 201)

        recipient_token, _ = Token.objects.get_or_create(user=self.recipient)
        recipient_client = APIClient()
        recipient_client.credentials(HTTP_AUTHORIZATION=f'Token {recipient_token.key}')
        received = recipient_client.get('/api/messagerie/messages/')
        self.assertEqual(received.status_code, 200)
        self.assertEqual(received.json()[0]['body'], 'Bonjour Moussa.')
        unread = recipient_client.get('/api/messagerie/non-lus/')
        self.assertEqual(unread.json()['private_count'], 1)
        opened = recipient_client.get(
            '/api/messagerie/messages/',
            {'contact_id': self.sender_profile.id},
        )
        self.assertEqual(opened.status_code, 200)
        self.assertEqual(opened.json()[0]['body'], 'Bonjour Moussa.')
        self.assertEqual(
            recipient_client.get('/api/messagerie/non-lus/').json()['private_count'],
            0,
        )

    def test_private_message_contact_filter_rejects_non_numeric_id(self):
        response = self.client.get(
            '/api/messagerie/messages/',
            {'contact_id': 'invalid'},
        )
        self.assertEqual(response.status_code, 400)

    def test_unread_parish_entity_count_clears_only_after_opening_its_conversation(self):
        entity = NotificationGroup.objects.create(name='Entité test')
        self.sender_profile.parish_entities.add(entity)
        state = ParishGroupReadState.objects.get(profile=self.sender_profile, entity=entity)
        state.last_read_at = timezone.now() - timedelta(minutes=5)
        state.save(update_fields=['last_read_at'])
        ParishGroupMessage.objects.create(
            entity=entity,
            sender=self.recipient_profile,
            body='Réunion dimanche.',
        )

        unread = self.client.get('/api/messagerie/non-lus/')
        self.assertEqual(unread.status_code, 200)
        self.assertEqual(unread.json()['entity_count'], 1)
        self.assertEqual(unread.json()['unread_entities'][0]['entity_name'], 'Entité test')

        self.client.get('/api/messagerie/entites/messages/')
        still_unread = self.client.get('/api/messagerie/non-lus/')
        self.assertEqual(still_unread.json()['entity_count'], 1)

        self.client.get('/api/messagerie/entites/messages/', {'entity_ids': entity.id})
        state.refresh_from_db()
        read = self.client.get('/api/messagerie/non-lus/')
        self.assertEqual(read.json()['entity_count'], 0)

    def test_user_cannot_read_messages_from_unjoined_entities_by_id(self):
        private_entity = NotificationGroup.objects.create(name='Entité privée')
        ParishGroupMessage.objects.create(
            entity=private_entity,
            sender=self.recipient_profile,
            body='Message réservé.',
        )

        response = self.client.get(
            '/api/messagerie/entites/messages/',
            {'entity_ids': private_entity.id},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_user_cannot_message_themselves(self):
        response = self.client.post('/api/messagerie/messages/', {
            'recipient_id': self.sender_profile.id,
            'body': 'Message impossible.',
        }, format='json')

        self.assertEqual(response.status_code, 400)

    def test_registration_adds_multiple_parish_entity_memberships(self):
        response = self.client.post('/api/auth/register/', {
            'first_name': 'Aminata',
            'last_name': 'Sow',
            'phone_number': '+221770000099',
            'parish_entity_names': ['Chorale', 'JEC'],
            'password': 'secret123',
        }, format='json')

        self.assertEqual(response.status_code, 201)
        profile = UserProfile.objects.get(user__username='+221770000099')
        self.assertEqual(
            set(profile.parish_entities.values_list('name', flat=True)),
            {'Chorale', 'JEC'},
        )
        self.assertEqual(profile.group.name, 'Chorale')

    def test_all_entities_are_available_and_messages_can_target_multiple_entities(self):
        entity, _ = NotificationGroup.objects.get_or_create(name='Choriste')
        second_entity, _ = NotificationGroup.objects.get_or_create(name='JEC')
        message_response = self.client.post('/api/messagerie/entites/messages/', {
            'entity_ids': [entity.id, second_entity.id],
            'body': 'Répétition samedi.',
        }, format='json')

        self.assertEqual(message_response.status_code, 201)
        self.assertEqual(ParishGroupMessage.objects.count(), 2)
        self.assertEqual(
            {item['entity']['name'] for item in message_response.json()},
            {'Choriste', 'JEC'},
        )
        self.assertTrue(all('phone_number' not in item['sender'] for item in message_response.json()))
        available_entities = self.client.get('/api/messagerie/entites/').json()
        available_names = {item['name'] for item in available_entities}
        self.assertTrue({'Choriste', 'JEC'} <= available_names)
        self.assertGreaterEqual(len(available_names), 12)

        self.recipient_profile.parish_entities.add(entity)
        recipient_token, _ = Token.objects.get_or_create(user=self.recipient)
        recipient_client = APIClient()
        recipient_client.credentials(HTTP_AUTHORIZATION=f'Token {recipient_token.key}')
        received = recipient_client.get('/api/messagerie/entites/messages/')
        self.assertEqual(received.status_code, 200)
        self.assertEqual(received.json()[0]['body'], 'Répétition samedi.')
        self.assertEqual(len(received.json()), 1)

        outsider = User.objects.create_user(username='+221771000022', password='demo123')
        UserProfile.objects.create(
            user=outsider, phone_number=outsider.username, first_name='Sali', last_name='Ndiaye', otp_verified=True
        )
        outsider_token, _ = Token.objects.get_or_create(user=outsider)
        outsider_client = APIClient()
        outsider_client.credentials(HTTP_AUTHORIZATION=f'Token {outsider_token.key}')
        hidden = outsider_client.get('/api/messagerie/entites/messages/')
        self.assertEqual(hidden.status_code, 200)
        self.assertEqual(hidden.json(), [])
        outgoing = outsider_client.post('/api/messagerie/entites/messages/', {
            'entity_ids': [entity.id],
            'body': 'Message destiné à la chorale.',
        }, format='json')
        self.assertEqual(outgoing.status_code, 201)
        self.assertEqual(outgoing.json()[0]['entity']['name'], 'Choriste')

    def test_message_can_target_more_than_twelve_entities(self):
        entities = [
            NotificationGroup.objects.create(name=f'Entité {index:02d}')
            for index in range(13)
        ]

        response = self.client.post('/api/messagerie/entites/messages/', {
            'entity_ids': [entity.id for entity in entities],
            'body': 'Message pour toutes les entités.',
        }, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(response.json()), 13)
        self.assertEqual(
            {message['entity']['id'] for message in response.json()},
            {entity.id for entity in entities},
        )

    def test_profile_can_update_multiple_parish_entity_memberships(self):
        response = self.client.put('/api/auth/profile/', {
            'first_name': 'Awa',
            'last_name': 'Diop',
            'parish_entity_names': ['Chorale', 'JEC'],
        }, format='json')

        self.assertEqual(response.status_code, 200)
        self.sender_profile.refresh_from_db()
        self.assertEqual(
            set(self.sender_profile.parish_entities.values_list('name', flat=True)),
            {'Chorale', 'JEC'},
        )

    def test_contact_search_returns_only_verified_users_without_phone_numbers(self):
        UserProfile.objects.create(
            user=User.objects.create_user(username='+221771000023'),
            phone_number='+221771000023',
            first_name='Aminata',
            last_name='Sow',
            otp_verified=True,
        )
        UserProfile.objects.create(
            user=User.objects.create_user(username='+221771000024'),
            phone_number='+221771000024',
            first_name='Aminata',
            last_name='Test',
            otp_verified=False,
        )

        response = self.client.get('/api/messagerie/contacts/?q=Aminata')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]['first_name'], 'Aminata')
        self.assertNotIn('phone_number', response.json()[0])


class PasswordAuthenticationTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_register_and_login_with_phone_and_password(self):
        register_response = self.client.post('/api/auth/register/', {
            'first_name': 'Awa',
            'last_name': 'Ndiaye',
            'phone_number': '+221770000001',
            'group_name': 'Chorale',
            'password': 'secret123',
        }, format='json')

        self.assertEqual(register_response.status_code, 201)
        self.assertIn('token', register_response.json())
        self.assertEqual(register_response.json()['profile']['group_name'], 'Chorale')

        login_response = self.client.post('/api/auth/login/', {
            'phone_number': '+221770000001',
            'password': 'secret123',
        }, format='json')

        self.assertEqual(login_response.status_code, 200)
        self.assertEqual(login_response.json()['token'], register_response.json()['token'])

    def test_auth_csrf_endpoint_sets_cookie_and_returns_token(self):
        client = APIClient(enforce_csrf_checks=True)
        response = client.get('/api/auth/csrf/')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['csrfToken'])
        self.assertIn('csrftoken', response.cookies)

        user = User.objects.create_user(username='+221770000004', password='secret123')
        login_response = client.post('/api/auth/login/', {
            'phone_number': user.username,
            'password': 'secret123',
        }, format='json', HTTP_X_CSRFTOKEN=response.json()['csrfToken'])

        self.assertEqual(login_response.status_code, 200)
        self.assertIn('token', login_response.json())

    def test_login_does_not_require_session_csrf_for_an_existing_browser_session(self):
        client = APIClient(enforce_csrf_checks=True)
        user = User.objects.create_user(username='+221770000005', password='secret123')
        client.force_login(user)

        response = client.post('/api/auth/login/', {
            'phone_number': user.username,
            'password': 'secret123',
        }, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertIn('token', response.json())

    def test_login_rejects_wrong_password(self):
        User.objects.create_user(username='+221770000002', password='secret123')

        response = self.client.post('/api/auth/login/', {
            'phone_number': '+221770000002',
            'password': 'wrongpass',
        }, format='json')

        self.assertEqual(response.status_code, 400)

    def test_register_completes_otp_created_account(self):
        self.client.post('/api/auth/request-otp/', {
            'phone_number': '+221770000003',
        }, format='json')

        response = self.client.post('/api/auth/register/', {
            'first_name': 'Mamadou',
            'last_name': 'Ba',
            'phone_number': '+221770000003',
            'group_name': 'Catéchiste',
            'password': 'secret123',
        }, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertTrue(User.objects.get(username='+221770000003').check_password('secret123'))

        login_response = self.client.post('/api/auth/login/', {
            'phone_number': '+221770000003',
            'password': 'secret123',
        }, format='json')
        self.assertEqual(login_response.status_code, 200)


class BibleQuizAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user, self.profile = self.create_parishioner('+221771009001', 'Awa')
        self.other_user, self.other_profile = self.create_parishioner('+221771009002', 'Moussa')
        self.user_token = Token.objects.get(user=self.user)
        self.other_token = Token.objects.get(user=self.other_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.user_token.key}')

    def create_parishioner(self, phone, first_name):
        user = User.objects.create_user(username=phone, password='demo123')
        profile = UserProfile.objects.create(
            user=user,
            phone_number=phone,
            first_name=first_name,
            last_name='Diop',
            otp_verified=True,
        )
        Token.objects.get_or_create(user=user)
        return user, profile

    def test_seed_covers_all_books_of_the_catholic_canon(self):
        old_testament_books = {
            'Genèse', 'Exode', 'Lévitique', 'Nombres', 'Deutéronome', 'Josué',
            'Juges', 'Ruth', '1 Samuel', '2 Samuel', '1 Rois', '2 Rois',
            '1 Chroniques', '2 Chroniques', 'Esdras', 'Néhémie', 'Tobie',
            'Judith', 'Esther', '1 Maccabées', '2 Maccabées', 'Job', 'Psaumes',
            'Proverbes', 'Qohélet', 'Cantique des Cantiques', 'Sagesse',
            'Siracide', 'Isaïe', 'Jérémie', 'Lamentations', 'Baruch', 'Ézéchiel',
            'Daniel', 'Osée', 'Joël', 'Amos', 'Abdias', 'Jonas', 'Michée',
            'Nahum', 'Habaquq', 'Sophonie', 'Aggée', 'Zacharie', 'Malachie',
        }
        new_testament_books = {
            'Matthieu', 'Marc', 'Luc', 'Jean', 'Actes des Apôtres', 'Romains',
            '1 Corinthiens', '2 Corinthiens', 'Galates', 'Éphésiens',
            'Philippiens', 'Colossiens', '1 Thessaloniciens',
            '2 Thessaloniciens', '1 Timothée', '2 Timothée', 'Tite', 'Philémon',
            'Hébreux', 'Jacques', '1 Pierre', '2 Pierre', '1 Jean', '2 Jean',
            '3 Jean', 'Jude', 'Apocalypse',
        }
        self.assertGreaterEqual(QuizQuestion.objects.count(), 1103)
        self.assertTrue(old_testament_books.issubset(set(
            QuizQuestion.objects.filter(testament='ancien').values_list('category', flat=True)
        )))
        self.assertTrue(new_testament_books.issubset(set(
            QuizQuestion.objects.filter(testament='nouveau').values_list('category', flat=True)
        )))
        for question in QuizQuestion.objects.all():
            self.assertEqual(len(question.options), 3)
            self.assertIn(question.correct_option, range(3))
            self.assertTrue(question.explanation)
        verse_questions = QuizQuestion.objects.filter(prompt__startswith='Complète le verset ')
        self.assertEqual(verse_questions.count(), 1000)
        self.assertEqual(
            verse_questions.values('category').distinct().count(), 73
        )
        self.assertEqual(
            verse_questions.values('prompt').distinct().count(), 1000
        )
        self.assertEqual(
            verse_questions.filter(explanation__contains='Bible Crampon (édition de 1923)').count(),
            1000,
        )

    def test_endpoints_require_authentication_and_random_question_hides_answer(self):
        anonymous = APIClient()
        self.assertEqual(anonymous.get('/api/quiz/questions/').status_code, 401)
        self.assertEqual(anonymous.get('/api/quiz/offline-pack/').status_code, 401)
        self.assertEqual(anonymous.post('/api/quiz/offline-results/', {}, format='json').status_code, 401)
        self.assertEqual(anonymous.post('/api/quiz/sessions/', {'mode': 'text'}, format='json').status_code, 401)
        self.assertEqual(
            anonymous.get('/api/quiz/sessions/1/speech/?question_id=1&segment=question').status_code,
            401,
        )

        response = self.client.get('/api/quiz/questions/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json()), {'id', 'category', 'prompt', 'options'})
        self.assertNotIn('correct_option', response.json())
        self.assertNotIn('explanation', response.json())

    def test_offline_pack_contains_answer_key_and_offline_results_are_idempotent(self):
        pack = self.client.get('/api/quiz/offline-pack/')
        self.assertEqual(pack.status_code, 200)
        self.assertEqual(len(pack.json()), 10)
        self.assertEqual(sum(question['testament'] == 'ancien' for question in pack.json()), 5)
        self.assertTrue(all('correct_option' in question and 'explanation' in question for question in pack.json()))

        questions = list(QuizQuestion.objects.filter(is_active=True).order_by('id')[:10])
        payload = {
            'client_session_id': 'local-test-session',
            'answers': [
                {'question_id': question.id, 'option_index': question.correct_option, 'timed_out': False}
                for question in questions
            ],
        }
        first = self.client.post(
            '/api/quiz/offline-results/',
            payload,
            format='json',
            HTTP_IDEMPOTENCY_KEY='offline-quiz-result-key',
        )
        replay = self.client.post(
            '/api/quiz/offline-results/',
            payload,
            format='json',
            HTTP_IDEMPOTENCY_KEY='offline-quiz-result-key',
        )
        self.assertEqual(first.status_code, 201)
        self.assertEqual(replay.status_code, 201)
        self.assertEqual(first.json(), replay.json())
        self.assertEqual(first.json()['correct_count'], 10)
        self.assertEqual(OfflineQuizResult.objects.filter(user=self.user).count(), 1)

        for timed_out, option_index in ((True, 0), (False, None)):
            invalid_payload = {
                'client_session_id': f'invalid-timeout-{timed_out}',
                'answers': [
                    {
                        'question_id': question.id,
                        'option_index': option_index,
                        'timed_out': timed_out,
                    }
                    for question in questions
                ],
            }
            invalid = self.client.post(
                '/api/quiz/offline-results/',
                invalid_payload,
                format='json',
            )
            self.assertEqual(invalid.status_code, 400)

        payload['answers'][0]['option_index'] = (payload['answers'][0]['option_index'] + 1) % 3
        conflict = self.client.post(
            '/api/quiz/offline-results/',
            payload,
            format='json',
            HTTP_IDEMPOTENCY_KEY='offline-quiz-result-key',
        )
        self.assertEqual(conflict.status_code, 409)

    def test_audio_session_speech_is_generated_for_the_owner_and_hides_unanswered_results(self):
        created = self.client.post(
            '/api/quiz/sessions/',
            {'mode': 'audio', 'wait_for_audio_completion': True},
            format='json',
        )
        self.assertEqual(created.status_code, 201)
        session_id = created.json()['id']
        question_id = created.json()['current_question']['id']

        with tempfile.NamedTemporaryFile(suffix='.wav') as audio_file:
            audio_file.write(b'RIFF-audio')
            audio_file.flush()
            with patch('api.quiz_views.synthesize_quiz_audio', return_value=Path(audio_file.name)) as synthesize:
                question_audio = self.client.get(
                    f'/api/quiz/sessions/{session_id}/speech/?question_id={question_id}&segment=question'
                )
                self.assertEqual(question_audio.status_code, 200)
                self.assertEqual(question_audio['Content-Type'], 'audio/wav')
                self.assertEqual(b''.join(question_audio.streaming_content), b'RIFF-audio')
                self.assertIn('Voici les réponses possibles', synthesize.call_args.args[0])

                unavailable_answer = self.client.get(
                    f'/api/quiz/sessions/{session_id}/speech/?question_id={question_id}&segment=answer'
                )
                self.assertEqual(unavailable_answer.status_code, 400)

                current = QuizSessionQuestion.objects.get(session_id=session_id, position=0)
                self.client.post(
                    f'/api/quiz/sessions/{session_id}/start/',
                    {},
                    format='json',
                )
                answered = self.client.post(
                    f'/api/quiz/sessions/{session_id}/answer/',
                    {
                        'question_id': current.question_id,
                        'option_index': current.question.correct_option,
                    },
                    format='json',
                )
                self.assertEqual(answered.status_code, 200)
                answer_audio = self.client.get(
                    f'/api/quiz/sessions/{session_id}/speech/?question_id={question_id}&segment=answer'
                )
                self.assertEqual(answer_audio.status_code, 200)
                self.assertIn('Bravo, c’est la bonne réponse.', synthesize.call_args.args[0])

                next_question = self.client.post(
                    f'/api/quiz/sessions/{session_id}/next/',
                    {},
                    format='json',
                )
                self.assertEqual(next_question.status_code, 200)
                stale_audio = self.client.get(
                    f'/api/quiz/sessions/{session_id}/speech/?question_id={question_id}&segment=question'
                )
                self.assertEqual(stale_audio.status_code, 409)

        other_client = APIClient()
        other_client.credentials(HTTP_AUTHORIZATION=f'Token {self.other_token.key}')
        self.assertEqual(
            other_client.get(
                f'/api/quiz/sessions/{session_id}/speech/?question_id={question_id}&segment=question'
            ).status_code,
            404,
        )

    def test_individual_session_answers_next_previous_and_protects_answer_key(self):
        created = self.client.post('/api/quiz/sessions/', {'mode': 'text'}, format='json')
        self.assertEqual(created.status_code, 201)
        data = created.json()
        session = QuizSession.objects.get(pk=data['id'])
        self.assertEqual(session.session_questions.count(), 10)
        self.assertEqual(
            session.session_questions.filter(question__testament='ancien').count(), 5
        )
        self.assertEqual(
            session.session_questions.filter(question__testament='nouveau').count(), 5
        )
        self.assertEqual(data['remaining_seconds'], 40)
        self.assertTrue(data['timer_running'])
        self.assertEqual(set(data['questions'][0]), {'id', 'category', 'prompt', 'options'})
        self.assertNotIn('correct_option', data['current_question'])
        question = QuizSessionQuestion.objects.get(session=session, position=0).question

        result = self.client.post(
            f"/api/quiz/sessions/{session.id}/answer/",
            {'question_id': question.id, 'option_index': question.correct_option},
            format='json',
        )
        self.assertEqual(result.status_code, 200)
        self.assertTrue(result.json()['current_question']['is_correct'])
        self.assertEqual(result.json()['current_question']['correct_option'], question.correct_option)
        self.assertEqual(result.json()['current_question']['explanation'], question.explanation)
        self.assertEqual(session.session_questions.count(), 10)

        next_response = self.client.post(f'/api/quiz/sessions/{session.id}/next/', {}, format='json')
        self.assertEqual(next_response.status_code, 200)
        self.assertEqual(next_response.json()['current_index'], 1)
        self.assertEqual(next_response.json()['correct_count'], 1)
        previous = self.client.post(f'/api/quiz/sessions/{session.id}/previous/', {}, format='json')
        self.assertEqual(previous.status_code, 200)
        self.assertEqual(previous.json()['current_index'], 0)
        self.assertEqual(previous.json()['current_question']['correct_option'], question.correct_option)

    def test_audio_session_timer_starts_only_after_audio_completion_signal(self):
        started = timezone.now()
        with patch('api.quiz_views.timezone.now', return_value=started):
            created = self.client.post(
                '/api/quiz/sessions/',
                {'mode': 'audio', 'wait_for_audio_completion': True},
                format='json',
            )
        self.assertEqual(created.status_code, 201)
        self.assertFalse(created.json()['timer_running'])
        self.assertEqual(created.json()['remaining_seconds'], 40)

        session_id = created.json()['id']
        session_question = QuizSessionQuestion.objects.get(session_id=session_id, position=0)
        self.assertIsNone(session_question.timer_started_at)
        early_answer = self.client.post(
            f'/api/quiz/sessions/{session_id}/answer/',
            {'question_id': session_question.question_id, 'option_index': 0},
            format='json',
        )
        self.assertEqual(early_answer.status_code, 400)

        with patch('api.quiz_views.timezone.now', return_value=started + timedelta(seconds=12)):
            fetched = self.client.get(f'/api/quiz/sessions/{session_id}/')
        self.assertFalse(fetched.json()['timer_running'])
        self.assertEqual(fetched.json()['remaining_seconds'], 40)

        with patch('api.quiz_views.timezone.now', return_value=started + timedelta(seconds=20)):
            timer_started = self.client.post(f'/api/quiz/sessions/{session_id}/start/', {}, format='json')
        self.assertTrue(timer_started.json()['timer_running'])
        self.assertEqual(timer_started.json()['remaining_seconds'], 40)
        session_question.refresh_from_db()
        self.assertEqual(session_question.timer_started_at, started + timedelta(seconds=20))

    def test_audio_answer_allows_advancing_before_timer_but_requires_an_answer(self):
        started = timezone.now()
        with patch('api.quiz_views.timezone.now', return_value=started):
            created = self.client.post(
                '/api/quiz/sessions/',
                {'mode': 'audio', 'wait_for_audio_completion': True},
                format='json',
            )
            session_id = created.json()['id']
            self.client.post(f'/api/quiz/sessions/{session_id}/start/', {}, format='json')

        session_question = QuizSessionQuestion.objects.get(session_id=session_id, position=0)
        question = session_question.question
        with patch('api.quiz_views.timezone.now', return_value=started + timedelta(seconds=10)):
            early_next = self.client.post(f'/api/quiz/sessions/{session_id}/next/', {}, format='json')
            self.assertEqual(early_next.status_code, 400)
            answered = self.client.post(
                f'/api/quiz/sessions/{session_id}/answer/',
                {'question_id': question.id, 'option_index': question.correct_option},
                format='json',
            )
        self.assertEqual(answered.status_code, 200)
        self.assertTrue(answered.json()['timer_running'])
        self.assertEqual(answered.json()['remaining_seconds'], 30)

        with patch('api.quiz_views.timezone.now', return_value=started + timedelta(seconds=20)):
            next_question = self.client.post(f'/api/quiz/sessions/{session_id}/next/', {}, format='json')
        self.assertEqual(next_question.status_code, 200)
        self.assertEqual(next_question.json()['current_index'], 1)

    def test_audio_session_without_deferred_timer_flag_keeps_legacy_behavior(self):
        created = self.client.post('/api/quiz/sessions/', {'mode': 'audio'}, format='json')
        self.assertEqual(created.status_code, 201)
        self.assertTrue(created.json()['timer_running'])

    def test_individual_pause_resume_preserves_time_and_timeout_reveals_answer(self):
        started = timezone.now()
        with patch('api.quiz_views.timezone.now', side_effect=lambda: started):
            created = self.client.post(
                '/api/quiz/sessions/',
                {'mode': 'audio', 'wait_for_audio_completion': True},
                format='json',
            )
        session_id = created.json()['id']

        with patch('api.quiz_views.timezone.now', side_effect=lambda: started):
            self.client.post(f'/api/quiz/sessions/{session_id}/start/', {}, format='json')

        with patch('api.quiz_views.timezone.now', side_effect=lambda: started + timedelta(seconds=12)):
            paused = self.client.post(f'/api/quiz/sessions/{session_id}/pause/', {}, format='json')
        self.assertEqual(paused.json()['status'], 'paused')
        self.assertEqual(paused.json()['remaining_seconds'], 28)

        with patch('api.quiz_views.timezone.now', side_effect=lambda: started + timedelta(seconds=200)):
            resumed = self.client.post(f'/api/quiz/sessions/{session_id}/resume/', {}, format='json')
        self.assertEqual(resumed.json()['status'], 'active')
        self.assertEqual(resumed.json()['remaining_seconds'], 28)
        self.assertFalse(resumed.json()['timer_running'])

        with patch('api.quiz_views.timezone.now', side_effect=lambda: started + timedelta(seconds=200)):
            resumed_timer = self.client.post(f'/api/quiz/sessions/{session_id}/start/', {}, format='json')
        self.assertTrue(resumed_timer.json()['timer_running'])

        question = QuizSessionQuestion.objects.get(session_id=session_id, position=0).question
        with patch('api.quiz_views.timezone.now', side_effect=lambda: started + timedelta(seconds=228)):
            timed_out = self.client.get(f'/api/quiz/sessions/{session_id}/')
        payload = timed_out.json()
        self.assertEqual(payload['current_index'], 0)
        self.assertEqual(payload['current_question']['question_id'], question.id)
        self.assertEqual(payload['answers'][0]['question_id'], question.id)
        self.assertTrue(payload['answers'][0]['timed_out'])
        self.assertEqual(payload['answers'][0]['correct_option'], question.correct_option)
        with patch('api.quiz_views.timezone.now', side_effect=lambda: started + timedelta(seconds=228)):
            next_question = self.client.post(f'/api/quiz/sessions/{session_id}/next/', {}, format='json')
        self.assertEqual(next_question.status_code, 200)
        self.assertEqual(next_question.json()['current_index'], 1)

    def test_challenge_acceptance_private_scoring_completion_and_rematch(self):
        created = self.client.post(
            '/api/quiz/challenges/',
            {'recipient_profile_id': self.other_profile.id},
            format='json',
        )
        self.assertEqual(created.status_code, 201)
        challenge_id = created.json()['id']
        self.assertEqual(created.json()['status'], 'pending')
        challenge = QuizChallenge.objects.get(pk=challenge_id)
        assignments = list(challenge.challenge_questions.select_related('question').order_by('position'))
        self.assertEqual(len(assignments), 10)
        self.assertEqual(
            challenge.challenge_questions.filter(question__testament='ancien').count(), 5
        )
        self.assertEqual(
            challenge.challenge_questions.filter(question__testament='nouveau').count(), 5
        )
        self.assertEqual(
            QuizChallengeParticipant.objects.filter(challenge=challenge).count(), 2
        )

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.other_token.key}')
        self.assertEqual(
            self.client.get(f'/api/quiz/challenges/{challenge_id}/').status_code, 200
        )
        accepted = self.client.post(f'/api/quiz/challenges/{challenge_id}/accept/', {}, format='json')
        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(accepted.json()['status'], 'active')
        self.assertFalse(accepted.json()['is_paused'])
        self.assertNotIn('correct_option', accepted.json()['current_question'])
        self.assertTrue(all('correct_option' not in item for item in accepted.json()['questions']))
        self.assertIsNone(accepted.json()['my_score'])

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.user_token.key}')
        for assignment in assignments:
            answer = self.client.post(
                f'/api/quiz/challenges/{challenge_id}/answer/',
                {'question_id': assignment.question_id, 'option_index': assignment.question.correct_option},
                format='json',
            )
            self.assertEqual(answer.status_code, 200)
            if assignment.position == 0:
                self.assertIsNone(answer.json()['my_score'])
                self.assertIsNone(answer.json()['result'])
        self.assertIsNone(self.client.get(f'/api/quiz/challenges/{challenge_id}/').json()['my_score'])

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.other_token.key}')
        for assignment in assignments:
            answer = self.client.post(
                f'/api/quiz/challenges/{challenge_id}/answer/',
                {'question_id': assignment.question_id, 'option_index': (assignment.question.correct_option + 1) % 3},
                format='json',
            )
            self.assertEqual(answer.status_code, 200)
        final = self.client.get(f'/api/quiz/challenges/{challenge_id}/')
        self.assertEqual(final.json()['status'], 'completed')
        self.assertEqual(final.json()['my_score'], 0)
        self.assertEqual(final.json()['opponent_score'], 10)
        self.assertEqual(final.json()['result']['winner_profile_id'], self.profile.id)
        self.assertEqual(final.json()['result']['outcome'], 'lost')
        self.assertFalse(final.json()['result']['is_tie'])

        rematch = self.client.post(f'/api/quiz/challenges/{challenge_id}/rematch/', {}, format='json')
        self.assertEqual(rematch.status_code, 201)
        self.assertEqual(rematch.json()['status'], 'pending')
        self.assertEqual(rematch.json()['opponent']['profile_id'], self.profile.id)
        self.assertNotEqual(rematch.json()['id'], challenge_id)
        self.assertTrue(QuizChallengeNotification.objects.filter(
            recipient=self.profile,
            challenge_id=rematch.json()['id'],
            kind='invitation',
            actor=self.other_profile,
        ).exists())

    def test_challenge_reports_a_tie_only_after_both_players_finish(self):
        created = self.client.post(
            '/api/quiz/challenges/',
            {'recipient_profile_id': self.other_profile.id},
            format='json',
        )
        challenge_id = created.json()['id']
        challenge = QuizChallenge.objects.get(pk=challenge_id)
        assignments = list(challenge.challenge_questions.select_related('question').order_by('position'))
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.other_token.key}')
        self.client.post(f'/api/quiz/challenges/{challenge_id}/accept/', {}, format='json')

        for token in (self.user_token, self.other_token):
            self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
            for assignment in assignments:
                response = self.client.post(
                    f'/api/quiz/challenges/{challenge_id}/answer/',
                    {
                        'question_id': assignment.question_id,
                        'option_index': assignment.question.correct_option,
                    },
                    format='json',
                )
                self.assertEqual(response.status_code, 200)
                if token == self.user_token and assignment.position == 9:
                    self.assertIsNone(response.json()['result'])

        result = self.client.get(f'/api/quiz/challenges/{challenge_id}/').json()['result']
        self.assertTrue(result['is_tie'])
        self.assertEqual(result['outcome'], 'draw')
        self.assertIsNone(result['winner_profile_id'])
        self.assertEqual([score['score'] for score in result['scores']], [10, 10])

    def test_challenge_notifications_cover_invitation_acceptance_and_refusal(self):
        anonymous = APIClient()
        self.assertEqual(anonymous.get('/api/quiz/notifications/').status_code, 401)

        created = self.client.post(
            '/api/quiz/challenges/',
            {'recipient_profile_id': self.other_profile.id},
            format='json',
        )
        challenge_id = created.json()['id']
        self.assertEqual(
            QuizChallengeNotification.objects.filter(
                recipient=self.other_profile,
                challenge_id=challenge_id,
                kind='invitation',
            ).count(),
            1,
        )

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.other_token.key}')
        notifications = self.client.get('/api/quiz/notifications/')
        self.assertEqual(notifications.status_code, 200)
        invitation = notifications.json()[0]
        self.assertEqual(invitation['kind'], 'invitation')
        self.assertEqual(invitation['challenge_id'], challenge_id)
        self.assertIn('Awa Diop vous a envoyé', invitation['message'])
        self.assertFalse(invitation['is_read'])
        read = self.client.post(
            f"/api/quiz/notifications/{invitation['id']}/read/", {}, format='json'
        )
        self.assertTrue(read.json()['is_read'])
        self.assertEqual(
            self.client.post(
                f'/api/quiz/challenges/{challenge_id}/accept/', {}, format='json'
            ).status_code,
            200,
        )

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.user_token.key}')
        response_notice = self.client.get('/api/quiz/notifications/').json()[0]
        self.assertEqual(response_notice['kind'], 'accepted')
        self.assertIn('Moussa Diop a accepté', response_notice['message'])

        second = self.client.post(
            '/api/quiz/challenges/',
            {'recipient_profile_id': self.other_profile.id},
            format='json',
        )
        second_id = second.json()['id']
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.other_token.key}')
        self.assertEqual(
            self.client.post(
                f'/api/quiz/challenges/{second_id}/decline/', {}, format='json'
            ).status_code,
            200,
        )
        self.assertTrue(QuizChallengeNotification.objects.get(
            recipient=self.other_profile,
            challenge_id=second_id,
            kind='invitation',
        ).is_read)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.user_token.key}')
        response_notice = self.client.get('/api/quiz/notifications/').json()[0]
        self.assertEqual(response_notice['kind'], 'declined')
        self.assertIn('Moussa Diop a refusé', response_notice['message'])

    def test_challenge_pause_timeout_decline_ownership_and_self_challenge_validation(self):
        self.assertEqual(
            self.client.post('/api/quiz/challenges/', {'recipient_profile_id': self.profile.id}, format='json').status_code,
            400,
        )
        created = self.client.post(
            '/api/quiz/challenges/',
            {'recipient_profile_id': self.other_profile.id},
            format='json',
        )
        challenge_id = created.json()['id']

        outsider_user, _ = self.create_parishioner('+221771009003', 'Saliou')
        outsider_token = Token.objects.get(user=outsider_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {outsider_token.key}')
        self.assertEqual(self.client.get(f'/api/quiz/challenges/{challenge_id}/').status_code, 404)

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.other_token.key}')
        declined = self.client.post(f'/api/quiz/challenges/{challenge_id}/decline/', {}, format='json')
        self.assertEqual(declined.status_code, 200)
        self.assertEqual(declined.json()['status'], 'declined')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.user_token.key}')
        rematch = self.client.post(f'/api/quiz/challenges/{challenge_id}/rematch/', {}, format='json')
        self.assertEqual(rematch.status_code, 201)
        self.assertEqual(rematch.json()['status'], 'pending')

        next_challenge_id = rematch.json()['id']
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.other_token.key}')
        self.client.post(f'/api/quiz/challenges/{next_challenge_id}/accept/', {}, format='json')
        now = timezone.now()
        with patch('api.quiz_views.timezone.now', side_effect=lambda: now + timedelta(seconds=20)):
            paused = self.client.post(f'/api/quiz/challenges/{next_challenge_id}/pause/', {}, format='json')
        self.assertEqual(paused.status_code, 200)
        self.assertEqual(paused.json()['remaining_seconds'], 70)
        self.assertTrue(paused.json()['is_paused'])
        with patch('api.quiz_views.timezone.now', side_effect=lambda: now + timedelta(seconds=200)):
            resumed = self.client.post(f'/api/quiz/challenges/{next_challenge_id}/resume/', {}, format='json')
        self.assertEqual(resumed.status_code, 200)
        self.assertEqual(resumed.json()['remaining_seconds'], 70)
        self.assertFalse(resumed.json()['is_paused'])
        with patch('api.quiz_views.timezone.now', side_effect=lambda: now + timedelta(seconds=270)):
            expired = self.client.get(f'/api/quiz/challenges/{next_challenge_id}/')
        self.assertTrue(expired.json()['my_responses'][0]['timed_out'])
        challenge = QuizChallenge.objects.get(pk=next_challenge_id)
        first_question = challenge.challenge_questions.order_by('position').first().question
        self.assertEqual(expired.json()['my_responses'][0]['question_id'], first_question.id)
        self.assertEqual(expired.json()['my_responses'][0]['correct_option'], first_question.correct_option)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.user_token.key}')
        with patch('api.quiz_views.timezone.now', side_effect=lambda: now + timedelta(seconds=270)):
            other_expired = self.client.get(f'/api/quiz/challenges/{next_challenge_id}/')
        self.assertEqual(other_expired.json()['status'], 'expired')
        self.assertEqual(other_expired.json()['result']['outcome'], 'draw')
