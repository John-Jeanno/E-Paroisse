import math
import random

from django.db import transaction
from django.db.models import Q
from django.http import FileResponse, Http404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .quiz_speech import SpeechUnavailableError, synthesize_quiz_audio
from .idempotency import idempotent
from .models import (
    QuizChallenge,
    QuizChallengeNotification,
    QuizChallengeParticipant,
    QuizChallengeQuestion,
    QuizChallengeResponse,
    OfflineQuizResult,
    QuizQuestion,
    QuizSession,
    QuizSessionQuestion,
    QuizSessionResponse,
    UserProfile,
)
from .quiz_serializers import (
    QuizAnswerSerializer,
    QuizChallengeCreateSerializer,
    OfflineQuizResultSerializer,
    QuizQuestionSerializer,
    QuizSessionCreateSerializer,
)

SESSION_QUESTION_SECONDS = 40
CHALLENGE_SECONDS = 90
QUESTION_COUNT = 10


def _challenge_notification_payload(notification):
    actor_name = f'{notification.actor.first_name} {notification.actor.last_name}'.strip() or 'Un paroissien'
    messages = {
        'invitation': f'{actor_name} vous a envoyé un défi biblique.',
        'accepted': f'{actor_name} a accepté votre défi biblique.',
        'declined': f'{actor_name} a refusé votre défi biblique.',
    }
    return {
        'id': notification.id,
        'kind': notification.kind,
        'challenge_id': notification.challenge_id,
        'actor_name': actor_name,
        'message': messages[notification.kind],
        'challenge_status': notification.challenge.status,
        'is_read': notification.is_read,
        'created_at': notification.created_at,
    }


def _profile(request):
    profile = UserProfile.objects.filter(user=request.user).first()
    if profile is None:
        return None, Response(
            {'detail': 'Un profil paroissial est nécessaire pour jouer.'},
            status=status.HTTP_403_FORBIDDEN,
        )
    return profile, None


def _random_questions():
    old_testament = list(
        QuizQuestion.objects.filter(is_active=True, testament='ancien')
    )
    new_testament = list(
        QuizQuestion.objects.filter(is_active=True, testament='nouveau')
    )
    questions_per_testament = QUESTION_COUNT // 2
    if (
        len(old_testament) < questions_per_testament
        or len(new_testament) < questions_per_testament
    ):
        return None
    questions = (
        random.sample(old_testament, questions_per_testament)
        + random.sample(new_testament, questions_per_testament)
    )
    random.shuffle(questions)
    return questions


def _public_question(question):
    return QuizQuestionSerializer(question).data


def _session_response_payload(session_question, response):
    question = session_question.question
    return {
        'question_id': question.id,
        'option_index': response.option_index,
        'is_correct': response.is_correct,
        'correct_option': question.correct_option,
        'explanation': question.explanation,
        'timed_out': response.timed_out,
    }


def _session_question_for(session, position):
    return session.session_questions.select_related('question').filter(position=position).first()


def _start_session_question(session_question, now, allow_answered=False):
    if (
        session_question
        and (allow_answered or not hasattr(session_question, 'response'))
        and not session_question.timer_started_at
    ):
        session_question.timer_started_at = now
        session_question.save(update_fields=['timer_started_at'])


def _capture_session_timer(session_question, now):
    if session_question and session_question.timer_started_at:
        elapsed = max(0, (now - session_question.timer_started_at).total_seconds())
        if elapsed >= session_question.remaining_seconds:
            session_question.remaining_seconds = 0
        else:
            session_question.remaining_seconds = max(
                0, math.ceil(session_question.remaining_seconds - elapsed)
            )
        session_question.timer_started_at = None
        session_question.save(update_fields=['remaining_seconds', 'timer_started_at'])


def _advance_session(session, now):
    session.current_index += 1
    if session.current_index >= QUESTION_COUNT:
        session.status = 'completed'
        session.completed_at = now
        session.save(update_fields=['current_index', 'status', 'completed_at'])
        return
    session.save(update_fields=['current_index'])
    if not session.timer_waits_for_audio:
        _start_session_question(_session_question_for(session, session.current_index), now)


def _sync_session_timeout(session, now):
    session_question = _session_question_for(session, session.current_index)
    if session.status != 'active' or session_question is None:
        return None
    has_response = hasattr(session_question, 'response')
    if session_question.timer_started_at is None:
        if not has_response and not session.timer_waits_for_audio:
            _start_session_question(session_question, now)
        return None

    elapsed = max(0, (now - session_question.timer_started_at).total_seconds())
    if elapsed < session_question.remaining_seconds:
        session_question.remaining_seconds = math.ceil(session_question.remaining_seconds - elapsed)
        session_question.timer_started_at = now
        session_question.save(update_fields=['remaining_seconds', 'timer_started_at'])
        return None

    session_question.remaining_seconds = 0
    session_question.timer_started_at = None
    session_question.save(update_fields=['remaining_seconds', 'timer_started_at'])
    if has_response:
        return None

    answer = QuizSessionResponse.objects.create(
        session_question=session_question,
        option_index=None,
        is_correct=False,
        timed_out=True,
    )
    result = _session_response_payload(session_question, answer)
    if session.mode != 'audio':
        _advance_session(session, now)
    return result


def _session_detail(session, now=None, latest_response=None):
    now = now or timezone.now()
    current = _session_question_for(session, session.current_index)
    remaining = None
    current_payload = None

    questions = list(session.session_questions.select_related('question').order_by('position'))
    answers = []
    for item in questions:
        response = getattr(item, 'response', None)
        if response:
            answers.append(_session_response_payload(item, response))
        if item.position == session.current_index:
            current_payload = _public_question(item.question)
            if response:
                current_payload.update(_session_response_payload(item, response))
            if session.status == 'active' and item.timer_started_at is not None:
                elapsed = max(0, (now - item.timer_started_at).total_seconds())
                remaining = max(0, math.ceil(item.remaining_seconds - elapsed))
            elif not response and session.status == 'active' and (
                not session.timer_waits_for_audio or item.timer_started_at is not None
            ):
                _start_session_question(item, now)
                elapsed = max(0, (now - item.timer_started_at).total_seconds())
                remaining = max(0, math.ceil(item.remaining_seconds - elapsed))
            elif session.status == 'paused':
                remaining = item.remaining_seconds
            else:
                remaining = item.remaining_seconds

    return {
        'id': session.id,
        'mode': session.mode,
        'status': session.status,
        'current_index': session.current_index,
        'total_questions': QUESTION_COUNT,
        'questions': [_public_question(item.question) for item in questions],
        'current_question': current_payload,
        'remaining_seconds': remaining,
        'timer_running': bool(
            session.status == 'active'
            and current is not None
            and current.timer_started_at is not None
        ),
        'correct_count': sum(1 for answer in answers if answer['is_correct']),
        'answers': answers,
        'latest_response': latest_response,
    }


class QuizQuestionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        question = QuizQuestion.objects.filter(is_active=True).order_by('?').first()
        if question is None:
            return Response(
                {'detail': 'Aucune question biblique n’est disponible.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(_public_question(question))


class QuizOfflinePackAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        old_testament = list(QuizQuestion.objects.filter(is_active=True, testament='ancien'))
        new_testament = list(QuizQuestion.objects.filter(is_active=True, testament='nouveau'))
        if len(old_testament) < 5 or len(new_testament) < 5:
            return Response(
                {'detail': 'Le quiz hors ligne nécessite au moins cinq questions de chaque Testament.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        questions = random.sample(old_testament, 5) + random.sample(new_testament, 5)
        random.shuffle(questions)
        return Response([
            {
                **_public_question(question),
                'testament': question.testament,
                'correct_option': question.correct_option,
                'explanation': question.explanation,
            }
            for question in questions
        ])


class QuizOfflineResultAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @idempotent
    def post(self, request):
        serializer = OfflineQuizResultSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        existing = OfflineQuizResult.objects.filter(
            user=request.user,
            client_session_id=values['client_session_id'],
        ).first()
        if existing:
            saved_answers = [
                (answer['question_id'], answer['option_index'], answer['timed_out'])
                for answer in existing.answers
            ]
            submitted_answers = [
                (answer['question_id'], answer['option_index'], answer['timed_out'])
                for answer in values['answers']
            ]
            if saved_answers != submitted_answers:
                return Response(
                    {'detail': 'Cet identifiant de partie a déjà été utilisé avec d’autres réponses.'},
                    status=status.HTTP_409_CONFLICT,
                )
            return Response({
                'client_session_id': existing.client_session_id,
                'correct_count': existing.correct_count,
                'total_questions': existing.total_questions,
                'answers': existing.answers,
            })

        question_ids = [answer['question_id'] for answer in values['answers']]
        questions = {
            question.id: question
            for question in QuizQuestion.objects.filter(id__in=question_ids)
        }
        if len(questions) != len(question_ids):
            return Response(
                {'detail': 'Une ou plusieurs questions de cette partie ne sont plus disponibles.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result_answers = []
        correct_count = 0
        for answer in values['answers']:
            question = questions[answer['question_id']]
            correct = answer['option_index'] == question.correct_option
            correct_count += int(correct)
            result_answers.append({
                **answer,
                'is_correct': correct,
                'correct_option': question.correct_option,
                'explanation': question.explanation,
            })
        result = OfflineQuizResult.objects.create(
            user=request.user,
            client_session_id=values['client_session_id'],
            answers=result_answers,
            correct_count=correct_count,
            total_questions=len(result_answers),
        )
        return Response({
            'client_session_id': result.client_session_id,
            'correct_count': result.correct_count,
            'total_questions': result.total_questions,
            'answers': result.answers,
        }, status=status.HTTP_201_CREATED)


class QuizChallengeNotificationListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile, error = _profile(request)
        if error:
            return error
        notifications = QuizChallengeNotification.objects.filter(
            recipient=profile,
        ).select_related('actor', 'challenge')[:50]
        return Response([
            _challenge_notification_payload(notification)
            for notification in notifications
        ])


class QuizChallengeNotificationReadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, notification_id):
        profile, error = _profile(request)
        if error:
            return error
        notification = QuizChallengeNotification.objects.filter(
            recipient=profile,
            pk=notification_id,
        ).first()
        if notification is None:
            raise Http404
        if not notification.is_read:
            notification.is_read = True
            notification.save(update_fields=['is_read'])
        return Response(_challenge_notification_payload(notification))


class QuizSessionListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        profile, error = _profile(request)
        if error:
            return error
        serializer = QuizSessionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        questions = _random_questions()
        if questions is None:
            return Response(
                {'detail': 'Le jeu nécessite au moins cinq questions actives dans chaque Testament.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        now = timezone.now()
        with transaction.atomic():
            wait_for_audio = (
                serializer.validated_data['mode'] == 'audio'
                and serializer.validated_data['wait_for_audio_completion']
            )
            session = QuizSession.objects.create(
                profile=profile,
                mode=serializer.validated_data['mode'],
                timer_waits_for_audio=wait_for_audio,
            )
            QuizSessionQuestion.objects.bulk_create([
                QuizSessionQuestion(
                    session=session,
                    question=question,
                    position=position,
                    remaining_seconds=SESSION_QUESTION_SECONDS,
                    timer_started_at=now if position == 0 and not wait_for_audio else None,
                )
                for position, question in enumerate(questions)
            ])
        return Response(_session_detail(session, now), status=status.HTTP_201_CREATED)


class QuizSessionTimerStartAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        with transaction.atomic():
            session = QuizSession.objects.select_for_update().filter(
                profile__user=request.user, pk=session_id
            ).first()
            if session is None:
                raise Http404
            now = timezone.now()
            session_question = _session_question_for(session, session.current_index)
            if (
                session.status != 'active'
                or session_question is None
                or hasattr(session_question, 'response')
            ):
                return Response({'detail': 'Le chronomètre de cette question ne peut pas démarrer.'}, status=400)
            _start_session_question(session_question, now)
            return Response(_session_detail(session, now))


class QuizSessionSpeechAPIView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'quiz_speech'

    def get(self, request, session_id):
        segment = request.query_params.get('segment')
        if segment not in {'question', 'answer'}:
            return Response({'detail': 'Le segment audio demandé est invalide.'}, status=400)
        try:
            question_id = int(request.query_params['question_id'])
        except (KeyError, TypeError, ValueError):
            return Response({'detail': 'La question audio demandée est invalide.'}, status=400)

        session = QuizSession.objects.filter(
            profile__user=request.user,
            pk=session_id,
            mode='audio',
        ).first()
        if session is None:
            raise Http404

        session_question = session.session_questions.select_related('question').filter(
            position=session.current_index,
            question_id=question_id,
        ).first()
        if session_question is None or session.status == 'completed':
            return Response(
                {'detail': 'La question a changé. Rechargez la voix française.'},
                status=status.HTTP_409_CONFLICT,
            )

        question = session_question.question
        if segment == 'question':
            labels = ['Première réponse', 'Deuxième réponse', 'Troisième réponse']
            choices = [
                f'{labels[index]} : {option}'
                for index, option in enumerate(question.options)
            ]
            text = (
                f'Écoute la question. {question.prompt}. '
                f'Voici les réponses possibles. {".".join(choices)}'
            )
        else:
            answer = getattr(session_question, 'response', None)
            if answer is None:
                return Response(
                    {'detail': 'La correction audio est disponible après la réponse.'},
                    status=400,
                )
            feedback = 'Bravo, c’est la bonne réponse.' if answer.is_correct else 'Pas tout à fait. La bonne réponse était'
            text = (
                f'{feedback} {question.options[question.correct_option]}. '
                f'{question.explanation}'
            )

        try:
            audio_path = synthesize_quiz_audio(text)
        except SpeechUnavailableError as error:
            return Response({'detail': str(error)}, status=503)

        response = FileResponse(
            audio_path.open('rb'),
            content_type='audio/wav',
            filename='quiz-francais.wav',
        )
        response['Cache-Control'] = 'private, max-age=86400'
        return response


class QuizSessionDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_session(self, request, session_id, lock=False):
        queryset = QuizSession.objects.filter(profile__user=request.user)
        if lock:
            queryset = queryset.select_for_update()
        session = queryset.filter(pk=session_id).first()
        if session is None:
            raise Http404
        return session

    def get(self, request, session_id):
        with transaction.atomic():
            session = self._get_session(request, session_id, lock=True)
            now = timezone.now()
            latest = _sync_session_timeout(session, now)
            return Response(_session_detail(session, now, latest))

    def post(self, request, session_id):
        serializer = QuizAnswerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            session = self._get_session(request, session_id, lock=True)
            now = timezone.now()
            latest = _sync_session_timeout(session, now)
            if latest:
                return Response(_session_detail(session, now, latest))
            if session.status != 'active':
                return Response({'detail': 'Cette partie n’est pas en cours.'}, status=400)
            session_question = _session_question_for(session, session.current_index)
            if session_question is None:
                return Response({'detail': 'Aucune question en cours.'}, status=400)
            values = serializer.validated_data
            if session.timer_waits_for_audio and session_question.timer_started_at is None:
                return Response(
                    {'detail': 'Écoutez la question avant de répondre.'},
                    status=400,
                )
            if values['question_id'] != session_question.question_id:
                return Response({'detail': 'Cette question ne correspond pas à la question actuelle.'}, status=400)
            if hasattr(session_question, 'response'):
                return Response({'detail': 'Une réponse a déjà été enregistrée pour cette question.'}, status=400)
            if values['option_index'] >= len(session_question.question.options):
                return Response({'option_index': ['Ce choix n’existe pas.']}, status=400)
            answer = QuizSessionResponse.objects.create(
                session_question=session_question,
                option_index=values['option_index'],
                is_correct=values['option_index'] == session_question.question.correct_option,
            )
            latest = _session_response_payload(session_question, answer)
            return Response(_session_detail(session, now, latest))


class QuizSessionNavigationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id, action):
        with transaction.atomic():
            session = QuizSession.objects.select_for_update().filter(
                profile__user=request.user, pk=session_id
            ).first()
            if session is None:
                raise Http404
            now = timezone.now()
            latest = _sync_session_timeout(session, now)
            if action == 'next':
                if latest:
                    return Response(_session_detail(session, now, latest))
                if session.status != 'active':
                    return Response({'detail': 'Cette partie n’est pas en cours.'}, status=400)
                current = _session_question_for(session, session.current_index)
                if current is None or not hasattr(current, 'response'):
                    if session.mode == 'audio' and current is not None and current.timer_started_at is not None:
                        return Response(
                            {'detail': 'Attendez la fin du chronomètre ou répondez avant de continuer.'},
                            status=400,
                        )
                    return Response({'detail': 'Répondez à la question avant de continuer.'}, status=400)
                _advance_session(session, now)
            else:
                if latest:
                    return Response(_session_detail(session, now, latest))
                if session.current_index == 0:
                    return Response({'detail': 'Il n’y a pas de question précédente.'}, status=400)
                _capture_session_timer(_session_question_for(session, session.current_index), now)
                session.current_index -= 1
                session.save(update_fields=['current_index'])
                if session.status == 'active' and not session.timer_waits_for_audio:
                    _start_session_question(_session_question_for(session, session.current_index), now)
                elif session.status == 'active' and session.mode == 'audio':
                    _start_session_question(
                        _session_question_for(session, session.current_index),
                        now,
                        allow_answered=True,
                    )
            return Response(_session_detail(session, now))


class QuizSessionPauseAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id, action):
        with transaction.atomic():
            session = QuizSession.objects.select_for_update().filter(
                profile__user=request.user, pk=session_id
            ).first()
            if session is None:
                raise Http404
            now = timezone.now()
            latest = _sync_session_timeout(session, now)
            if action == 'pause':
                if session.status == 'active':
                    _capture_session_timer(_session_question_for(session, session.current_index), now)
                    session.status = 'paused'
                    session.save(update_fields=['status'])
            elif session.status == 'paused':
                session.status = 'active'
                session.save(update_fields=['status'])
                current = _session_question_for(session, session.current_index)
                if not session.timer_waits_for_audio:
                    _start_session_question(_session_question_for(session, session.current_index), now)
                elif current and hasattr(current, 'response') and current.remaining_seconds > 0:
                    _start_session_question(current, now, allow_answered=True)
            else:
                return Response({'detail': 'Cette partie ne peut pas être reprise.'}, status=400)
            return Response(_session_detail(session, now, latest))


def _challenge_response_payload(challenge_question, response):
    question = challenge_question.question
    return {
        'question_id': question.id,
        'option_index': response.option_index,
        'is_correct': response.is_correct,
        'correct_option': question.correct_option,
        'explanation': question.explanation,
        'timed_out': response.timed_out,
    }


def _participant_for(challenge, profile, lock=False):
    queryset = challenge.participants.select_related('profile')
    if lock:
        queryset = queryset.select_for_update()
    return queryset.filter(profile=profile).first()


def _challenge_question_for(challenge, position):
    return challenge.challenge_questions.select_related('question').filter(position=position).first()


def _challenge_finish_if_ready(challenge, now):
    participants = list(challenge.participants.all())
    if len(participants) == 2 and all(participant.finished_at for participant in participants):
        challenge.status = 'expired' if any(participant.timed_out for participant in participants) else 'completed'
        challenge.completed_at = now
        challenge.save(update_fields=['status', 'completed_at'])


def _sync_challenge_participant(challenge, participant, now):
    if challenge.status != 'active' or participant.finished_at or participant.is_paused:
        return None
    if participant.timer_started_at is None:
        participant.timer_started_at = now
        participant.save(update_fields=['timer_started_at'])
        return None
    elapsed = max(0, (now - participant.timer_started_at).total_seconds())
    if elapsed < participant.remaining_seconds:
        participant.remaining_seconds = math.ceil(participant.remaining_seconds - elapsed)
        participant.timer_started_at = now
        participant.save(update_fields=['remaining_seconds', 'timer_started_at'])
        return None

    participant.remaining_seconds = 0
    participant.timer_started_at = None
    participant.timed_out = True
    participant.finished_at = now
    current = _challenge_question_for(challenge, participant.current_index)
    result = None
    if current and not QuizChallengeResponse.objects.filter(
        participant=participant, challenge_question=current
    ).exists():
        response = QuizChallengeResponse.objects.create(
            participant=participant,
            challenge_question=current,
            option_index=None,
            is_correct=False,
            timed_out=True,
        )
        result = _challenge_response_payload(current, response)
    participant.save(update_fields=[
        'remaining_seconds', 'timer_started_at', 'timed_out', 'finished_at'
    ])
    _challenge_finish_if_ready(challenge, now)
    return result


def _challenge_summary(challenge, profile):
    opponent = challenge.recipient if challenge.challenger_id == profile.id else challenge.challenger
    participant = _participant_for(challenge, profile)
    return {
        'id': challenge.id,
        'status': challenge.status,
        'opponent': {
            'profile_id': opponent.id,
            'first_name': opponent.first_name,
            'last_name': opponent.last_name,
        },
        'is_incoming': challenge.recipient_id == profile.id,
        'current_index': participant.current_index if participant else 0,
        'remaining_seconds': participant.remaining_seconds if participant else None,
        'is_paused': participant.is_paused if participant else True,
        'created_at': challenge.created_at,
    }


def _challenge_detail(challenge, profile, latest_response=None, now=None):
    now = now or timezone.now()
    participant = _participant_for(challenge, profile)
    if participant is None:
        raise Http404
    current = _challenge_question_for(challenge, participant.current_index)
    current_payload = _public_question(current.question) if current else None
    responses = list(
        participant.responses.select_related(
            'challenge_question__question'
        ).order_by('challenge_question__position')
    )
    answer_payloads = [
        _challenge_response_payload(response.challenge_question, response)
        for response in responses
    ]
    remaining = participant.remaining_seconds
    if challenge.status == 'active' and not participant.finished_at and not participant.is_paused:
        if participant.timer_started_at:
            elapsed = max(0, (now - participant.timer_started_at).total_seconds())
            remaining = max(0, math.ceil(participant.remaining_seconds - elapsed))
    if current and current_payload:
        current_response = next(
            (item for item in responses if item.challenge_question_id == current.id), None
        )
        if current_response:
            current_payload.update(_challenge_response_payload(current, current_response))

    finished = challenge.status in ('completed', 'expired')
    result = None
    my_score = None
    opponent_score = None
    outcome = None
    if finished:
        scores = []
        for player in challenge.participants.select_related('profile').all():
            score = player.responses.filter(is_correct=True).count()
            scores.append({'profile_id': player.profile_id, 'score': score})
        if len(scores) == 2:
            opponent_profile = challenge.recipient if challenge.challenger_id == profile.id else challenge.challenger
            if scores[0]['score'] == scores[1]['score']:
                winner_id = None
            else:
                winner_id = max(scores, key=lambda score: score['score'])['profile_id']
            my_score = next((item['score'] for item in scores if item['profile_id'] == profile.id), 0)
            opponent_score = next(
                (item['score'] for item in scores if item['profile_id'] == opponent_profile.id),
                0,
            )
            outcome = 'draw' if winner_id is None else 'won' if winner_id == profile.id else 'lost'
            result = {
                'scores': scores,
                'winner_profile_id': winner_id,
                'is_tie': winner_id is None,
                'outcome': outcome,
            }

    return {
        **_challenge_summary(challenge, profile),
        'current_index': participant.current_index,
        'total_questions': QUESTION_COUNT,
        'questions': [
            _public_question(item.question)
            for item in challenge.challenge_questions.select_related('question').order_by('position')
        ],
        'current_question': current_payload,
        'remaining_seconds': remaining,
        'my_responses': answer_payloads,
        'latest_response': latest_response,
        'my_score': my_score,
        'opponent_score': opponent_score,
        'result': result,
    }


class QuizChallengeListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile, error = _profile(request)
        if error:
            return error
        challenges = QuizChallenge.objects.filter(
            Q(challenger=profile) | Q(recipient=profile)
        ).select_related('challenger', 'recipient').prefetch_related('participants').order_by('-created_at')
        return Response([_challenge_summary(challenge, profile) for challenge in challenges])

    def post(self, request):
        profile, error = _profile(request)
        if error:
            return error
        serializer = QuizChallengeCreateSerializer(
            data=request.data, context={'profile': profile}
        )
        serializer.is_valid(raise_exception=True)
        questions = _random_questions()
        if questions is None:
            return Response(
                {'detail': 'Le jeu nécessite au moins cinq questions actives dans chaque Testament.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        with transaction.atomic():
            challenge = QuizChallenge.objects.create(
                challenger=profile, recipient=serializer.validated_data['recipient']
            )
            QuizChallengeNotification.objects.get_or_create(
                recipient=serializer.validated_data['recipient'],
                challenge=challenge,
                kind='invitation',
                defaults={'actor': profile},
            )
            QuizChallengeParticipant.objects.bulk_create([
                QuizChallengeParticipant(challenge=challenge, profile=profile),
                QuizChallengeParticipant(challenge=challenge, profile=serializer.validated_data['recipient']),
            ])
            QuizChallengeQuestion.objects.bulk_create([
                QuizChallengeQuestion(challenge=challenge, question=question, position=position)
                for position, question in enumerate(questions)
            ])
        return Response(_challenge_summary(challenge, profile), status=status.HTTP_201_CREATED)


class QuizChallengeDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_challenge(self, request, challenge_id, lock=False):
        profile = UserProfile.objects.filter(user=request.user).first()
        if profile is None:
            raise Http404
        queryset = QuizChallenge.objects.filter(Q(challenger=profile) | Q(recipient=profile))
        if lock:
            queryset = queryset.select_for_update()
        challenge = queryset.filter(pk=challenge_id).first()
        if challenge is None:
            raise Http404
        return challenge

    def get(self, request, challenge_id):
        profile, error = _profile(request)
        if error:
            return error
        with transaction.atomic():
            challenge = self._get_challenge(request, challenge_id, lock=True)
            participant = _participant_for(challenge, profile, lock=True)
            now = timezone.now()
            latest = _sync_challenge_participant(challenge, participant, now)
            return Response(_challenge_detail(challenge, profile, latest, now))


class QuizChallengeActionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, challenge_id, action):
        profile, error = _profile(request)
        if error:
            return error
        with transaction.atomic():
            challenge = QuizChallenge.objects.select_for_update().filter(
                (Q(challenger=profile) | Q(recipient=profile)), pk=challenge_id
            ).first()
            if challenge is None:
                raise Http404
            participant = _participant_for(challenge, profile, lock=True)
            now = timezone.now()
            latest = _sync_challenge_participant(challenge, participant, now)

            if latest and action not in ('accept', 'decline', 'rematch'):
                return Response(_challenge_detail(challenge, profile, latest, now))

            if action in ('accept', 'decline'):
                if profile != challenge.recipient or challenge.status != 'pending':
                    return Response({'detail': 'Ce défi ne peut pas être traité.'}, status=400)
                QuizChallengeNotification.objects.filter(
                    recipient=profile,
                    challenge=challenge,
                    kind='invitation',
                    is_read=False,
                ).update(is_read=True)
                if action == 'decline':
                    challenge.status = 'declined'
                    challenge.completed_at = now
                    challenge.save(update_fields=['status', 'completed_at'])
                    QuizChallengeNotification.objects.get_or_create(
                        recipient=challenge.challenger,
                        challenge=challenge,
                        kind='declined',
                        defaults={'actor': profile},
                    )
                else:
                    challenge.status = 'active'
                    challenge.accepted_at = now
                    challenge.save(update_fields=['status', 'accepted_at'])
                    QuizChallengeNotification.objects.get_or_create(
                        recipient=challenge.challenger,
                        challenge=challenge,
                        kind='accepted',
                        defaults={'actor': profile},
                    )
                    for player in challenge.participants.select_for_update():
                        player.is_paused = False
                        player.timer_started_at = now
                        player.remaining_seconds = CHALLENGE_SECONDS
                        player.save(update_fields=['is_paused', 'timer_started_at', 'remaining_seconds'])
                return Response(_challenge_detail(challenge, profile, latest, now))

            if action == 'rematch':
                if challenge.status not in ('completed', 'expired', 'declined'):
                    return Response({'detail': 'Le défi doit être terminé avant une revanche.'}, status=400)
                questions = _random_questions()
                if questions is None:
                    return Response(
                        {'detail': 'Le jeu nécessite au moins cinq questions actives dans chaque Testament.'},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE,
                    )
                opponent = challenge.recipient if challenge.challenger_id == profile.id else challenge.challenger
                rematch = QuizChallenge.objects.create(challenger=profile, recipient=opponent)
                QuizChallengeNotification.objects.get_or_create(
                    recipient=opponent,
                    challenge=rematch,
                    kind='invitation',
                    defaults={'actor': profile},
                )
                QuizChallengeParticipant.objects.bulk_create([
                    QuizChallengeParticipant(challenge=rematch, profile=profile),
                    QuizChallengeParticipant(challenge=rematch, profile=opponent),
                ])
                QuizChallengeQuestion.objects.bulk_create([
                    QuizChallengeQuestion(challenge=rematch, question=question, position=position)
                    for position, question in enumerate(questions)
                ])
                return Response(_challenge_summary(rematch, profile), status=status.HTTP_201_CREATED)

            if action in ('pause', 'quit'):
                if challenge.status != 'active' or participant.finished_at:
                    return Response({'detail': 'Ce défi ne peut pas être mis en pause.'}, status=400)
                if participant.timer_started_at:
                    elapsed = max(0, (now - participant.timer_started_at).total_seconds())
                    participant.remaining_seconds = max(
                        0, math.ceil(participant.remaining_seconds - elapsed)
                    )
                participant.timer_started_at = None
                participant.is_paused = True
                participant.save(update_fields=['remaining_seconds', 'timer_started_at', 'is_paused'])
            elif action == 'resume':
                if challenge.status != 'active' or participant.finished_at:
                    return Response({'detail': 'Ce défi ne peut pas être repris.'}, status=400)
                participant.is_paused = False
                participant.timer_started_at = now
                participant.save(update_fields=['is_paused', 'timer_started_at'])
            elif action == 'answer':
                if latest:
                    return Response(_challenge_detail(challenge, profile, latest, now))
                if challenge.status != 'active' or participant.finished_at or participant.is_paused:
                    return Response({'detail': 'Votre participation n’est pas en cours.'}, status=400)
                serializer = QuizAnswerSerializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                current = _challenge_question_for(challenge, participant.current_index)
                if current is None:
                    return Response({'detail': 'Aucune question en cours.'}, status=400)
                values = serializer.validated_data
                if values['question_id'] != current.question_id:
                    return Response({'detail': 'Cette question ne correspond pas à la question actuelle.'}, status=400)
                if values['option_index'] >= len(current.question.options):
                    return Response({'option_index': ['Ce choix n’existe pas.']}, status=400)
                if QuizChallengeResponse.objects.filter(
                    participant=participant, challenge_question=current
                ).exists():
                    return Response({'detail': 'Une réponse a déjà été enregistrée pour cette question.'}, status=400)
                response = QuizChallengeResponse.objects.create(
                    participant=participant,
                    challenge_question=current,
                    option_index=values['option_index'],
                    is_correct=values['option_index'] == current.question.correct_option,
                )
                latest = _challenge_response_payload(current, response)
                participant.current_index += 1
                if participant.current_index >= QUESTION_COUNT:
                    participant.finished_at = now
                    participant.timer_started_at = None
                    participant.is_paused = True
                participant.save(update_fields=['current_index', 'finished_at', 'timer_started_at', 'is_paused'])
                _challenge_finish_if_ready(challenge, now)
            else:
                return Response({'detail': 'Action inconnue.'}, status=404)
            return Response(_challenge_detail(challenge, profile, latest, now))
