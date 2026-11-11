import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ActivityIndicator, AppState, Platform, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { setAudioModeAsync, useAudioPlayer, useAudioPlayerStatus } from 'expo-audio';
import { useFocusEffect, useRoute } from '@react-navigation/native';
import type { RouteProp } from '@react-navigation/native';
import type { RootStackParamList } from '../navigation/AppNavigator';
import type { MessagingProfile } from '../api/messagingService';
import { fetchMessagingContacts } from '../api/messagingService';
import { getToken } from '../api/tokenStorage';
import { getConnectivity } from '../api/connectivityState';
import { getOfflineAccountKey } from '../api/offlineStorage';
import {
    answerQuizChallenge,
    answerQuizQuestion,
    createQuizChallenge,
    createOfflineQuizSession,
    createQuizSession,
    fetchQuizChallenge,
    fetchQuizChallenges,
    fetchQuizSession,
    moveQuizQuestion,
    QuizAnswer,
    QuizChallenge,
    QuizOpponent,
    QuizQuestion,
    QuizSession,
    getQuizSpeechUrl,
    startQuizQuestionTimer,
    updateQuizChallenge,
    updateQuizSessionPause,
} from '../api/quizService';
import { useTheme } from '../theme/LiturgicalTheme';
import useResponsiveLayout from '../hooks/useResponsiveLayout';

type GameMode = 'solo' | 'online';
type ChallengeTab = 'received' | 'sent';

const profileLabel = (profile: MessagingProfile) =>
    `${profile.first_name} ${profile.last_name}`.trim() || profile.group_name || 'Paroissien';
const opponentLabel = (opponent: QuizOpponent) =>
    `${opponent.first_name} ${opponent.last_name}`.trim() || 'Paroissien';
const SAVED_SESSION_KEY = 'spiritualQuizSavedSession';
const SAVED_SESSION_MODE_KEY = 'spiritualQuizSavedSessionMode';

async function getSavedSessionKeys() {
    const accountKey = getOfflineAccountKey(await getToken());
    return {
        id: `${SAVED_SESSION_KEY}:${accountKey}`,
        mode: `${SAVED_SESSION_MODE_KEY}:${accountKey}`,
    };
}

async function clearSavedSession() {
    const keys = await getSavedSessionKeys();
    await Promise.all([
        AsyncStorage.removeItem(keys.id),
        AsyncStorage.removeItem(keys.mode),
    ]);
}

function formatTime(seconds: number) {
    const safeSeconds = Math.max(0, seconds);
    return `${Math.floor(safeSeconds / 60).toString().padStart(2, '0')}:${(safeSeconds % 60).toString().padStart(2, '0')}`;
}

function getSessionAnswer(session: QuizSession | null): QuizAnswer | undefined {
    if (!session) return undefined;
    return session.current_answer
        || session.answers?.find((answer) => answer.question_id === session.current_question?.id);
}

export default function SpiritualGameScreen() {
    const theme = useTheme();
    const route = useRoute<RouteProp<RootStackParamList, 'SpiritualGame'>>();
    const { contentMaxWidth, horizontalPadding } = useResponsiveLayout();
    const manualAudioPlayback = Platform.OS === 'web';
    const [mode, setMode] = useState<GameMode>('solo');
    const [challengeTab, setChallengeTab] = useState<ChallengeTab>('received');
    const [session, setSession] = useState<QuizSession | null>(null);
    const [sessionIdInput, setSessionIdInput] = useState<number | null>(null);
    const [savedSessionMode, setSavedSessionMode] = useState<'audio' | 'text' | null>(null);
    const [challenges, setChallenges] = useState<QuizChallenge[]>([]);
    const [contacts, setContacts] = useState<MessagingProfile[]>([]);
    const [activeChallenge, setActiveChallenge] = useState<QuizChallenge | null>(null);
    const [remainingSeconds, setRemainingSeconds] = useState(0);
    const [selectedOption, setSelectedOption] = useState<number | null>(null);
    const [audioMode, setAudioMode] = useState(false);
    const [speechFailed, setSpeechFailed] = useState(false);
    const [speechSourceKey, setSpeechSourceKey] = useState<string | null>(null);
    const [speechLoading, setSpeechLoading] = useState(false);
    const [speechLoadAttempt, setSpeechLoadAttempt] = useState(0);
    const [playingSpeechKey, setPlayingSpeechKey] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [busy, setBusy] = useState(false);
    const speechPlayer = useAudioPlayer(null, { updateInterval: 100 });
    const speechStatus = useAudioPlayerStatus(speechPlayer);
    const previousAnswer = useRef<string | null>(null);
    const playbackKeyRef = useRef<string | null>(null);
    const playbackDoneRef = useRef<(() => void) | undefined>(undefined);
    const playbackHandledRef = useRef<string | null>(null);
    const playbackStartedRef = useRef<string | null>(null);
    const autoPlaybackStartedRef = useRef<string | null>(null);
    const timerStartInFlight = useRef<number | null>(null);
    const autoAdvanceAnswerKey = useRef<string | null>(null);
    const moveSoloRef = useRef<(direction: 'next' | 'previous') => Promise<void>>(async () => {});
    const openedChallengeId = useRef<number | null>(null);
    const isOnline = mode === 'online';

    const stopSpeech = useCallback(async () => {
        speechPlayer.pause();
        playbackKeyRef.current = null;
        playbackDoneRef.current = undefined;
        setPlayingSpeechKey(null);
    }, [speechPlayer]);

    const startAudioTimer = useCallback(async (sessionId: number) => {
        if (timerStartInFlight.current === sessionId) return;
        timerStartInFlight.current = sessionId;
        try {
            const updated = await startQuizQuestionTimer(sessionId);
            setSession((current) => current?.id === sessionId ? updated : current);
            setRemainingSeconds(updated.remaining_seconds);
            setError('');
        } catch {
            setError('Impossible de démarrer le chronomètre après la lecture audio. Vérifiez votre connexion.');
        } finally {
            if (timerStartInFlight.current === sessionId) timerStartInFlight.current = null;
        }
    }, []);

    const refreshChallenges = useCallback(async () => {
        try {
            setChallenges(await fetchQuizChallenges());
            setError('');
        } catch {
            setError('Impossible de charger les défis pour le moment.');
        }
    }, []);

    const refreshActiveChallenge = useCallback(async (id: number) => {
        try {
            const current = await fetchQuizChallenge(id);
            setActiveChallenge(current);
            setRemainingSeconds(current.remaining_seconds ?? 0);
            if (current.status === 'completed' || current.status === 'expired') {
                await refreshChallenges();
            }
        } catch {
            setError('Le défi n’a pas pu être actualisé. Vérifiez votre connexion.');
        }
    }, [refreshChallenges]);

    useFocusEffect(useCallback(() => {
        if (mode === 'online') {
            void refreshChallenges();
            void fetchMessagingContacts().then(setContacts).catch(() => {
                setError('Impossible de charger la liste des paroissiens.');
            });
            const refreshInterval = setInterval(() => {
                if (AppState.currentState === 'active') void refreshChallenges();
            }, 6000);
            const appStateListener = AppState.addEventListener('change', (state) => {
                if (state === 'active') void refreshChallenges();
            });
            return () => {
                clearInterval(refreshInterval);
                appStateListener.remove();
                void stopSpeech();
            };
        }
        return () => {
            void stopSpeech();
        };
    }, [mode, refreshChallenges, stopSpeech]));

    useEffect(() => {
        const challengeId = route.params?.challengeId;
        if (!challengeId || openedChallengeId.current === challengeId) return;
        openedChallengeId.current = challengeId;
        setMode('online');
        setChallengeTab('received');
        void fetchQuizChallenge(challengeId)
            .then(setActiveChallenge)
            .catch(() => setError('Le défi de la notification n’a pas pu être ouvert.'));
    }, [route.params?.challengeId]);

    useEffect(() => {
        let mounted = true;
        getSavedSessionKeys()
            .then((keys) => Promise.all([
                AsyncStorage.getItem(keys.id),
                AsyncStorage.getItem(keys.mode),
            ]))
            .then(([savedId, savedMode]) => {
                if (!mounted) return;
                if (savedId) setSessionIdInput(Number(savedId));
                if (savedMode === 'audio' || savedMode === 'text') setSavedSessionMode(savedMode);
            })
            .catch(() => setError('Impossible de lire la partie sauvegardée.'));
        return () => {
            mounted = false;
        };
    }, []);

    useEffect(() => {
        if (!activeChallenge || activeChallenge.status !== 'active') return;
        const timer = setInterval(() => {
            if (!activeChallenge.is_paused && AppState.currentState === 'active') {
                setRemainingSeconds((seconds) => {
                    if (seconds <= 1) {
                        void refreshActiveChallenge(activeChallenge.id);
                        return 0;
                    }
                    return seconds - 1;
                });
            }
        }, 1000);
        const subscription = AppState.addEventListener('change', (state) => {
            if (state === 'active') void refreshActiveChallenge(activeChallenge.id);
        });
        const poll = setInterval(() => void refreshActiveChallenge(activeChallenge.id), 4000);
        return () => {
            clearInterval(timer);
            clearInterval(poll);
            subscription.remove();
        };
    }, [activeChallenge?.id, activeChallenge?.status, activeChallenge?.is_paused, refreshActiveChallenge]);

    const currentQuestion = session?.current_question ?? null;
    const currentAnswer = getSessionAnswer(session);
    const spokenAnswerKey = currentAnswer
        ? `${session?.id}:${currentQuestion?.id}:${currentAnswer.timed_out}:${currentAnswer.option_index}`
        : null;
    const speechSegment = currentAnswer ? 'answer' : 'question';
    const speechRequestKey = session && currentQuestion && audioMode
        ? `${session.id}:${currentQuestion.id}:${speechSegment}:${spokenAnswerKey ?? ''}`
        : null;
    const speechObjectUrl = useRef<string | null>(null);

    useEffect(() => {
        if (!audioMode || !session || session.mode !== 'audio' || !currentQuestion || !speechRequestKey) {
            speechPlayer.pause();
            speechPlayer.replace(null);
            setSpeechSourceKey(null);
            setSpeechLoading(false);
            return undefined;
        }

        let cancelled = false;
        speechPlayer.pause();
        speechPlayer.replace(null);
        setSpeechSourceKey(null);
        setSpeechLoading(true);
        setSpeechFailed(false);
        setError('');

        const prepareAudio = async () => {
            try {
                const token = await getToken();
                if (!token) throw new Error('Votre session a expiré. Reconnectez-vous pour écouter le jeu.');

                const url = getQuizSpeechUrl(session.id, currentQuestion.id, speechSegment);
                const headers = { Authorization: `Token ${token}` };
                if (Platform.OS === 'web') {
                    const response = await fetch(url, { headers });
                    if (!response.ok) {
                        throw new Error(response.status === 503
                            ? 'La voix française est momentanément indisponible.'
                            : response.status === 409
                                ? 'La question a changé pendant le chargement. Réessayez la lecture.'
                                : 'Impossible de préparer la lecture audio.');
                    }
                    const audioUrl = URL.createObjectURL(await response.blob());
                    if (cancelled) {
                        URL.revokeObjectURL(audioUrl);
                        return;
                    }
                    speechObjectUrl.current = audioUrl;
                    speechPlayer.replace({ uri: audioUrl });
                } else {
                    speechPlayer.replace({ uri: url, headers });
                }
                setSpeechSourceKey(speechRequestKey);
                setSpeechLoading(false);
            } catch (caughtError: unknown) {
                if (cancelled) return;
                setSpeechLoading(false);
                setSpeechFailed(true);
                setError(caughtError instanceof Error
                    ? caughtError.message
                    : 'Impossible de préparer la voix française. Vérifiez votre connexion puis réessayez.');
            }
        };
        void prepareAudio();

        return () => {
            cancelled = true;
            if (speechObjectUrl.current) {
                URL.revokeObjectURL(speechObjectUrl.current);
                speechObjectUrl.current = null;
            }
        };
    }, [audioMode, currentQuestion?.id, session?.id, session?.mode, speechLoadAttempt, speechPlayer, speechRequestKey, speechSegment]);

    useEffect(() => {
        if (Platform.OS === 'web' || !audioMode) return;
        void setAudioModeAsync({ playsInSilentMode: true, allowsRecording: false })
            .catch(() => setError('Le lecteur audio de l’application n’a pas pu être activé.'));
    }, [audioMode]);

    useEffect(() => {
        speechPlayer.pause();
        playbackKeyRef.current = null;
        playbackDoneRef.current = undefined;
        playbackStartedRef.current = null;
        setPlayingSpeechKey(null);
    }, [speechPlayer, speechRequestKey]);

    const speechReady = Boolean(
        speechRequestKey
        && speechSourceKey === speechRequestKey
        && speechStatus.isLoaded,
    );

    const playCurrentAudio = useCallback(async (onDone?: () => void) => {
        if (!speechRequestKey || !speechReady) {
            if (!speechLoading && !speechFailed) {
                setError('La voix française est encore en préparation. Réessayez dans quelques secondes.');
            }
            return;
        }

        playbackKeyRef.current = speechRequestKey;
        playbackDoneRef.current = onDone;
        playbackHandledRef.current = null;
        playbackStartedRef.current = null;
        setSpeechFailed(false);
        setError('');
        setPlayingSpeechKey(speechRequestKey);
        try {
            await speechPlayer.seekTo(0);
            if (playbackKeyRef.current !== speechRequestKey) return;
            speechPlayer.play();
        } catch {
            if (playbackKeyRef.current !== speechRequestKey) return;
            playbackKeyRef.current = null;
            playbackDoneRef.current = undefined;
            setPlayingSpeechKey(null);
            setSpeechFailed(true);
            setError('La lecture de la voix française a échoué. Réessayez.');
        }
    }, [speechFailed, speechLoading, speechPlayer, speechReady, speechRequestKey]);

    const onCurrentSpeechFinished = useCallback(() => {
        if (!session || !currentQuestion) return;
        if (currentAnswer) {
            if (!manualAudioPlayback) {
                autoAdvanceAnswerKey.current = spokenAnswerKey;
                void moveSoloRef.current('next');
            }
        } else if (!session.timer_running) {
            void startAudioTimer(session.id);
        }
    }, [currentAnswer, currentQuestion, manualAudioPlayback, session, spokenAnswerKey, startAudioTimer]);

    useEffect(() => {
        if (!speechStatus.error || speechSourceKey !== speechRequestKey) return;
        setSpeechFailed(true);
        setError('La voix française n’a pas pu être chargée. Vérifiez votre connexion puis réessayez.');
    }, [speechRequestKey, speechSourceKey, speechStatus.error]);

    useEffect(() => {
        if (
            speechRequestKey
            && speechReady
            && speechStatus.playing
            && speechStatus.currentTime > 0
            && playbackKeyRef.current === speechRequestKey
        ) {
            playbackStartedRef.current = speechRequestKey;
        }
    }, [speechReady, speechRequestKey, speechStatus.currentTime, speechStatus.playing]);

    useEffect(() => {
        if (
            !speechRequestKey
            || !speechReady
            || speechStatus.playing
            || !speechStatus.didJustFinish
            || playbackKeyRef.current !== speechRequestKey
            || playbackStartedRef.current !== speechRequestKey
            || playbackHandledRef.current === speechRequestKey
        ) return;

        playbackHandledRef.current = speechRequestKey;
        playbackKeyRef.current = null;
        playbackStartedRef.current = null;
        setPlayingSpeechKey(null);
        setSpeechFailed(false);
        playbackDoneRef.current?.();
        playbackDoneRef.current = undefined;
    }, [speechReady, speechRequestKey, speechStatus.didJustFinish, speechStatus.playing]);

    useEffect(() => {
        if (
            manualAudioPlayback
            || !audioMode
            || session?.status !== 'active'
            || !speechReady
            || autoPlaybackStartedRef.current === speechRequestKey
        ) return;

        autoPlaybackStartedRef.current = speechRequestKey;
        playCurrentAudio(onCurrentSpeechFinished);
    }, [audioMode, manualAudioPlayback, onCurrentSpeechFinished, playCurrentAudio, session?.status, speechReady, speechRequestKey]);

    useEffect(() => {
        if (!session || session.status !== 'active' || !session.timer_running) return;
        const timer = setInterval(() => {
            setRemainingSeconds((seconds) => {
                if (seconds <= 1) {
                    void fetchQuizSession(session.id).then((updated) => {
                        setSession(updated);
                        setRemainingSeconds(updated.remaining_seconds);
                    }).catch(() => setError('Impossible de vérifier le chronomètre.'));
                    return 0;
                }
                return seconds - 1;
            });
        }, 1000);
        return () => clearInterval(timer);
    }, [session?.id, session?.status, session?.timer_running, currentQuestion?.id, Boolean(currentAnswer)]);

    const startSession = async (voice: boolean) => {
        setBusy(true);
        setError('');
        try {
            let started: QuizSession;
            let startedOffline = false;
            try {
                started = await createQuizSession(voice ? 'audio' : 'text');
            } catch (caughtError: unknown) {
                if (voice || getConnectivity() !== false) throw caughtError;
                started = await createOfflineQuizSession();
                startedOffline = true;
            }
            const keys = await getSavedSessionKeys();
            await Promise.all([
                AsyncStorage.setItem(keys.id, String(started.id)),
                AsyncStorage.setItem(keys.mode, started.mode),
            ]);
            setAudioMode(started.mode === 'audio');
            setSavedSessionMode(started.mode);
            setSpeechFailed(false);
            setSession(started);
            setSessionIdInput(started.id);
            setRemainingSeconds(started.remaining_seconds);
            setSelectedOption(null);
            previousAnswer.current = null;
            autoAdvanceAnswerKey.current = null;
            if (startedOffline) {
                setError('Partie hors ligne : vos réponses sont enregistrées sur cet appareil et le résultat sera synchronisé à la reconnexion.');
            }
        } catch (caughtError: unknown) {
            setError(voice && caughtError instanceof Error
                ? caughtError.message
                : voice
                    ? 'Impossible de démarrer le mode audio. Vérifiez les autorisations audio et votre connexion, puis réessayez.'
                    : 'Impossible de démarrer le jeu. Connectez-vous puis réessayez.');
            setSpeechFailed(voice);
        } finally {
            setBusy(false);
        }
    };

    const resumeSession = async () => {
        if (!sessionIdInput) return;
        setBusy(true);
        try {
            const resumed = await fetchQuizSession(sessionIdInput);
            if (resumed.status === 'completed') {
                await clearSavedSession();
                setSessionIdInput(null);
                setSavedSessionMode(null);
                setError('La partie sauvegardée est déjà terminée.');
                return;
            }
            setSession(resumed);
            setAudioMode(resumed.mode === 'audio');
            setSavedSessionMode(resumed.mode);
            setSpeechFailed(false);
            setRemainingSeconds(resumed.remaining_seconds);
            setSelectedOption(null);
            previousAnswer.current = null;
            autoAdvanceAnswerKey.current = null;
        } catch (caughtError: unknown) {
            setError(caughtError instanceof Error
                ? caughtError.message
                : 'La partie sauvegardée est introuvable.');
        } finally {
            setBusy(false);
        }
    };

    const submitSoloAnswer = async (optionIndex: number) => {
        if (!session?.current_question || currentAnswer || busy) return;
        setBusy(true);
        setSelectedOption(optionIndex);
        try {
            const updated = await answerQuizQuestion(session.id, session.current_question.id, optionIndex);
            setSession(updated);
            setRemainingSeconds(updated.remaining_seconds);
        } catch {
            setError('Votre réponse n’a pas pu être enregistrée.');
            setSelectedOption(null);
        } finally {
            setBusy(false);
        }
    };

    const retryCurrentAudio = () => {
        if (!session?.current_question) return;
        if (speechReady) {
            playCurrentAudio(onCurrentSpeechFinished);
        } else {
            setSpeechFailed(false);
            setSpeechLoading(true);
            setSpeechLoadAttempt((attempt) => attempt + 1);
            setError('');
        }
    };

    const moveSolo = async (direction: 'next' | 'previous') => {
        if (
            !session
            || (direction === 'next'
                && session.mode === 'audio'
                && !currentAnswer)
        ) return;
        if (direction === 'previous') {
            autoAdvanceAnswerKey.current = null;
            previousAnswer.current = null;
            autoPlaybackStartedRef.current = null;
            void stopSpeech();
        }
        setBusy(true);
        try {
            const updated = await moveQuizQuestion(session.id, direction);
            if (updated.status === 'completed') {
                await clearSavedSession();
                setSessionIdInput(null);
                setSavedSessionMode(null);
            }
            previousAnswer.current = null;
            autoAdvanceAnswerKey.current = null;
            setSession(updated);
            setRemainingSeconds(updated.remaining_seconds);
            setSelectedOption(null);
            setError('');
        } catch {
            setError(direction === 'previous' ? 'Vous êtes déjà à la première question.' : 'Impossible de passer à la question suivante.');
        } finally {
            setBusy(false);
        }
    };
    moveSoloRef.current = moveSolo;

    const toggleSessionPause = async () => {
        if (!session) return;
        setBusy(true);
        try {
            const isPausing = session.status !== 'paused';
            if (isPausing) {
                await stopSpeech();
                previousAnswer.current = null;
                autoAdvanceAnswerKey.current = null;
                autoPlaybackStartedRef.current = null;
            }
            const updated = await updateQuizSessionPause(session.id, isPausing ? 'pause' : 'resume');
            setSession(updated);
            setRemainingSeconds(updated.remaining_seconds);
        } catch {
            setError('Impossible de mettre la partie en pause ou de la reprendre.');
        } finally {
            setBusy(false);
        }
    };

    const finishSession = () => {
        void stopSpeech();
        void clearSavedSession().catch(() => setError('Impossible de supprimer la partie sauvegardée.'));
        setSession(null);
        setSessionIdInput(null);
        setSavedSessionMode(null);
        setAudioMode(false);
        setSelectedOption(null);
    };

    const sendChallenge = async (profile: MessagingProfile) => {
        setBusy(true);
        try {
            const challenge = await createQuizChallenge(profile.id);
            setActiveChallenge(challenge);
            await refreshChallenges();
        } catch {
            setError(`Impossible de lancer le défi contre ${profileLabel(profile)}.`);
        } finally {
            setBusy(false);
        }
    };

    const answerChallenge = async (optionIndex: number) => {
        if (!activeChallenge?.current_question || busy) return;
        setBusy(true);
        try {
            setActiveChallenge(await answerQuizChallenge(
                activeChallenge.id,
                activeChallenge.current_question.id,
                optionIndex,
            ));
        } catch {
            setError('Votre réponse au défi n’a pas pu être enregistrée.');
        } finally {
            setBusy(false);
        }
    };

    const performChallengeAction = async (challenge: QuizChallenge, action: 'accept' | 'decline' | 'pause' | 'resume' | 'quit' | 'rematch') => {
        setBusy(true);
        try {
            const result = await updateQuizChallenge(challenge.id, action);
            if (action === 'decline') {
                await refreshChallenges();
                return;
            }
            if (action === 'quit') {
                setActiveChallenge(null);
                await refreshChallenges();
                return;
            }
            setActiveChallenge(result);
            setRemainingSeconds(result.remaining_seconds ?? 0);
            await refreshChallenges();
        } catch {
            setError('Cette action sur le défi n’a pas pu être effectuée.');
        } finally {
            setBusy(false);
        }
    };

    const renderModePicker = () => (
        <View style={[styles.modePicker, { borderColor: theme.accent }]}>
            {(['solo', 'online'] as GameMode[]).map((item) => (
                <Pressable key={item} onPress={() => { setMode(item); setError(''); setActiveChallenge(null); }} style={[styles.modeButton, mode === item && { backgroundColor: theme.primary }]}>
                    <Text style={[styles.modeButtonText, { color: mode === item ? '#fff' : theme.primary }]}>
                        {item === 'solo' ? '🎯  Jouer seul' : '⚔️  Défi en ligne'}
                    </Text>
                </Pressable>
            ))}
        </View>
    );

    const sortedChallenges = useMemo(
        () => [...challenges].sort((a, b) => Number(a.status !== 'pending') - Number(b.status !== 'pending')),
        [challenges],
    );
    const receivedChallenges = sortedChallenges.filter((challenge) => challenge.is_incoming);
    const sentChallenges = sortedChallenges.filter((challenge) => !challenge.is_incoming);
    const visibleChallenges = challengeTab === 'received' ? receivedChallenges : sentChallenges;

    return (
        <ScrollView style={{ backgroundColor: theme.background }} contentContainerStyle={[styles.container, { maxWidth: contentMaxWidth, paddingHorizontal: horizontalPadding }]}>
            <View style={[styles.hero, { backgroundColor: theme.primary }]}>
                <Text style={styles.heroIcon}>📖</Text>
                <View style={styles.heroCopy}>
                    <Text style={styles.heroTitle}>Jeux spirituels</Text>
                    <Text style={styles.heroText}>Teste tes connaissances bibliques, seul ou avec un paroissien.</Text>
                </View>
            </View>
            {renderModePicker()}
            {error ? <Text style={styles.error}>{error}</Text> : null}
            {isOnline ? (
                <View style={styles.content}>
                    {activeChallenge ? (
                        <View style={[styles.card, { backgroundColor: theme.card, borderColor: theme.accent }]}>
                            <Pressable onPress={() => { setActiveChallenge(null); void refreshChallenges(); }} accessibilityRole="button">
                                <Text style={[styles.back, { color: theme.primary }]}>← Mes défis</Text>
                            </Pressable>
                            {renderChallenge(activeChallenge, theme, remainingSeconds, answerChallenge, performChallengeAction, busy)}
                        </View>
                    ) : (
                        <>
                            <Text style={[styles.heading, { color: theme.text }]}>Défier un paroissien</Text>
                            <Text style={[styles.description, { color: theme.text }]}>Même série de 10 questions tirées des deux Testaments · 90 secondes par joueur.</Text>
                            <View style={styles.contactList}>
                                {contacts.map((contact) => (
                                    <Pressable key={contact.id} disabled={busy} onPress={() => void sendChallenge(contact)} style={[styles.contactCard, { backgroundColor: theme.card, borderColor: theme.accent }]}>
                                        <Text style={styles.contactIcon}>👤</Text>
                                        <View style={styles.contactCopy}>
                                            <Text style={[styles.contactName, { color: theme.text }]}>{profileLabel(contact)}</Text>
                                            {contact.group_name ? <Text style={[styles.contactGroup, { color: theme.text }]}>{contact.group_name}</Text> : null}
                                        </View>
                                        <Text style={[styles.challengeAction, { color: theme.primary }]}>Défier →</Text>
                                    </Pressable>
                                ))}
                                {contacts.length === 0 ? <Text style={[styles.description, { color: theme.text }]}>Aucun autre paroissien disponible pour le moment.</Text> : null}
                            </View>
                            <Text style={[styles.heading, { color: theme.text, marginTop: 24 }]}>Mes défis</Text>
                            <View style={[styles.challengeTabs, { borderColor: theme.accent }]}>
                                {(['received', 'sent'] as ChallengeTab[]).map((tab) => {
                                    const count = tab === 'received' ? receivedChallenges.length : sentChallenges.length;
                                    const selected = challengeTab === tab;
                                    return (
                                        <Pressable
                                            key={tab}
                                            accessibilityRole="button"
                                            accessibilityState={{ selected }}
                                            onPress={() => setChallengeTab(tab)}
                                            style={[styles.challengeTab, selected && { backgroundColor: theme.primary }]}
                                        >
                                            <Text style={[styles.challengeTabText, { color: selected ? '#fff' : theme.primary }]}>
                                                {tab === 'received' ? 'Reçus' : 'Envoyés'} ({count})
                                            </Text>
                                        </Pressable>
                                    );
                                })}
                            </View>
                            {visibleChallenges.map((challenge) => (
                                <ChallengeRow
                                    key={challenge.id}
                                    challenge={challenge}
                                    theme={theme}
                                    onOpen={() => {
                                        if (challenge.status === 'pending') {
                                            setActiveChallenge(challenge);
                                        } else {
                                            void fetchQuizChallenge(challenge.id).then(setActiveChallenge).catch(() => setError('Impossible d’ouvrir ce défi.'));
                                        }
                                    }}
                                    onAction={(action) => void performChallengeAction(challenge, action)}
                                    busy={busy}
                                />
                            ))}
                            {visibleChallenges.length === 0 ? (
                                <Text style={[styles.description, { color: theme.text }]}>
                                    {challengeTab === 'received' ? 'Aucun défi reçu pour le moment.' : 'Vous n’avez envoyé aucun défi pour le moment.'}
                                </Text>
                            ) : null}
                        </>
                    )}
                </View>
            ) : session ? (
                <View style={[styles.card, { backgroundColor: theme.card, borderColor: theme.accent }]}>
                    <Pressable onPress={() => setSession(null)} accessibilityRole="button">
                        <Text style={[styles.back, { color: theme.primary }]}>← Quitter la vue (partie sauvegardée)</Text>
                    </Pressable>
                    {renderSession(
                        session,
                        currentQuestion,
                        currentAnswer,
                        remainingSeconds,
                        selectedOption,
                        theme,
                        submitSoloAnswer,
                        moveSolo,
                        toggleSessionPause,
                        finishSession,
                        retryCurrentAudio,
                        speechFailed,
                        speechLoading || (speechSourceKey === speechRequestKey && !speechReady),
                        speechReady,
                        playingSpeechKey === speechRequestKey,
                        busy,
                        manualAudioPlayback,
                    )}
                </View>
            ) : (
                <View style={[styles.card, { backgroundColor: theme.card, borderColor: theme.accent }]}>
                    <Text style={[styles.heading, { color: theme.text }]}>Choisis ton mode de jeu</Text>
                    <Text style={[styles.description, { color: theme.text }]}>10 questions aléatoires tirées à parts égales de l’Ancien et du Nouveau Testament. Tu as 40 secondes pour répondre à chacune. À la fin du temps, la bonne réponse est révélée à l’écran et lue à voix haute si tu as choisi le mode audio.</Text>
                    <View style={styles.choiceRow}>
                        <Pressable disabled={busy} onPress={() => void startSession(false)} style={[styles.choiceCard, { borderColor: theme.accent, backgroundColor: theme.background }]}>
                            <Text style={styles.choiceIcon}>📝</Text>
                            <Text style={[styles.choiceTitle, { color: theme.text }]}>Mode écrit</Text>
                            <Text style={[styles.choiceHint, { color: theme.text }]}>Lire les questions</Text>
                        </Pressable>
                        <Pressable disabled={busy} onPress={() => void startSession(true)} style={[styles.choiceCard, { borderColor: theme.accent, backgroundColor: theme.background }]}>
                            <Text style={styles.choiceIcon}>🔊</Text>
                            <Text style={[styles.choiceTitle, { color: theme.text }]}>Mode audio</Text>
                            <Text style={[styles.choiceHint, { color: theme.text }]}>Écouter questions et réponses</Text>
                        </Pressable>
                    </View>
                    <Text style={[styles.smallHint, { color: theme.text }]}>
                        La même voix française intégrée est utilisée sur iPhone, Android, PWA et ordinateur. Une connexion Internet est nécessaire pour préparer les fichiers audio.
                    </Text>
                    {sessionIdInput ? (
                        <Pressable disabled={busy} onPress={() => void resumeSession()} style={[styles.resumeButton, { borderColor: theme.primary }]}>
                            <Text style={[styles.resumeText, { color: theme.primary }]}>Reprendre ma partie sauvegardée</Text>
                        </Pressable>
                    ) : null}
                    {busy ? <ActivityIndicator color={theme.primary} /> : null}
                </View>
            )}
        </ScrollView>
    );
}

function renderSession(
    session: QuizSession,
    question: QuizSession['current_question'],
    answer: QuizAnswer | undefined,
    remaining: number,
    selectedOption: number | null,
    theme: ReturnType<typeof useTheme>,
    onAnswer: (optionIndex: number) => Promise<void>,
    onMove: (direction: 'next' | 'previous') => Promise<void>,
    onPause: () => Promise<void>,
    onFinish: () => void,
    onRetryAudio: () => void,
    speechFailed: boolean,
    speechLoading: boolean,
    speechReady: boolean,
    speechPlaying: boolean,
    busy: boolean,
    manualAudioPlayback: boolean,
) {
    if (session.status === 'completed') {
        const totalQuestions = session.questions.length;
        const doubledScore = session.correct_count * 2;
        const outcome = doubledScore > totalQuestions
            ? 'won'
            : doubledScore === totalQuestions
                ? 'draw'
                : 'lost';
        const result = outcome === 'won'
            ? { title: 'Tu as gagné cette partie !', icon: '🏆' }
            : outcome === 'draw'
                ? { title: 'Partie nulle !', icon: '🤝' }
                : { title: 'Tu as perdu cette partie.', icon: '📖' };
        return (
            <View style={styles.result}>
                <Text style={styles.resultIcon}>{result.icon}</Text>
                <Text style={[styles.heading, { color: theme.text }]}>{result.title}</Text>
                <Text style={[styles.description, { color: theme.text }]}>Tu as obtenu {session.correct_count} bonne(s) réponse(s) sur {totalQuestions}.</Text>
                <Pressable onPress={onFinish} style={[styles.mainAction, { backgroundColor: theme.primary }]}>
                    <Text style={styles.mainActionText}>Continuer</Text>
                </Pressable>
            </View>
        );
    }

    const revealedAnswer = answer;

    return (
        <>
            <View style={styles.gameTopRow}>
                <Text style={[styles.progress, { color: theme.text }]}>Question {(session.current_index ?? 0) + 1} / {session.questions.length}</Text>
                <Text style={[styles.timer, { color: !session.offline && remaining <= 10 ? '#b42318' : theme.primary }]}>
                    {session.offline ? '⏱ Hors ligne · sans chrono' : `⏱ ${formatTime(remaining)}`}
                </Text>
            </View>
            <View style={[styles.progressTrack, { backgroundColor: theme.accent }]}>
                <View style={[styles.progressFill, { width: `${((session.current_index + 1) / session.questions.length) * 100}%`, backgroundColor: theme.primary }]} />
            </View>
            {question ? (
                <>
                    <Text style={[styles.category, { color: theme.primary }]}>{question.category}</Text>
                    <Text style={[styles.question, { color: theme.text }]}>{question.prompt}</Text>
                    {session.mode === 'audio'
                        && session.status === 'active'
                        && !answer
                        && (manualAudioPlayback || !session.timer_running) ? (
                        <>
                            <Text style={[styles.smallHint, { color: theme.text }]}>
                                {manualAudioPlayback
                                    ? session.timer_running
                                        ? 'La voix française intégrée lit la question et ses choix. Le chronomètre continue pendant la lecture.'
                                        : 'La voix française intégrée lit la question et ses choix. Le chronomètre démarrera après la lecture.'
                                    : 'La question et ses choix vont être lus automatiquement, puis le chronomètre démarrera.'}
                            </Text>
                            {manualAudioPlayback || speechFailed ? (
                                <Pressable
                                    accessibilityRole="button"
                                    disabled={speechLoading || speechPlaying || (!speechReady && !speechFailed)}
                                    onPress={onRetryAudio}
                                    style={[styles.secondaryAction, { borderColor: theme.primary, alignSelf: 'flex-start' }]}
                                >
                                    <Text style={[styles.secondaryActionText, { color: theme.primary }]}>
                                        {speechFailed
                                            ? '🔁 Réessayer la voix française'
                                            : speechLoading
                                                ? 'Préparation de la voix française…'
                                                : speechPlaying
                                                    ? '🔊 Lecture de la question…'
                                                    : '🔊 Écouter la question'}
                                    </Text>
                                </Pressable>
                            ) : null}
                        </>
                    ) : null}
                    {session.mode === 'audio' && answer && (manualAudioPlayback || speechFailed) ? (
                        <View style={styles.navigationRow}>
                            <Pressable
                                accessibilityRole="button"
                                disabled={speechLoading || speechPlaying || (!speechReady && !speechFailed)}
                                onPress={onRetryAudio}
                                style={[styles.secondaryAction, { borderColor: theme.primary }]}
                            >
                                <Text style={[styles.secondaryActionText, { color: theme.primary }]}>
                                    {speechFailed
                                        ? '🔁 Réessayer la voix française'
                                        : speechLoading
                                            ? 'Préparation de la voix française…'
                                            : speechPlaying
                                                ? '🔊 Lecture de la correction…'
                                                : '🔊 Écouter la correction'}
                                </Text>
                            </Pressable>
                            <Pressable
                                accessibilityRole="button"
                                disabled={busy}
                                onPress={() => void onMove('next')}
                                style={[styles.mainAction, { backgroundColor: theme.primary }]}
                            >
                                <Text style={styles.mainActionText}>
                                    {manualAudioPlayback ? 'Passer la correction →' : 'Continuer sans audio →'}
                                </Text>
                            </Pressable>
                        </View>
                    ) : null}
                    <View style={styles.options}>
                        {question.options.map((option, index) => {
                            const isCorrect = revealedAnswer?.correct_option === index;
                            const isWrongChoice = revealedAnswer?.option_index === index && !revealedAnswer.is_correct;
                            return (
                                <Pressable
                                    key={`${question.id}-${index}`}
                                    disabled={Boolean(answer) || busy || session.status !== 'active' || (session.mode === 'audio' && !session.timer_running)}
                                    onPress={() => void onAnswer(index)}
                                    style={[
                                        styles.option,
                                        { borderColor: theme.accent, backgroundColor: theme.background },
                                        selectedOption === index && !answer && { borderColor: theme.primary },
                                        revealedAnswer && isCorrect && styles.correctOption,
                                        revealedAnswer && isWrongChoice && styles.wrongOption,
                                    ]}
                                >
                                    <Text style={[styles.optionLetter, { backgroundColor: revealedAnswer && isCorrect ? '#198754' : theme.primary }]}>{String.fromCharCode(65 + index)}</Text>
                                    <Text style={[styles.optionText, { color: theme.text }]}>{option}</Text>
                                </Pressable>
                            );
                        })}
                    </View>
                    {revealedAnswer ? (
                        <View style={[styles.explanation, { backgroundColor: theme.background, borderColor: theme.accent }]}>
                            <Text style={[styles.answerFeedback, { color: revealedAnswer.is_correct ? '#198754' : '#b42318' }]}>
                                {revealedAnswer.timed_out ? '⏰ Temps écoulé — voici la réponse.' : revealedAnswer.is_correct ? '✓ Bonne réponse !' : '✗ Ce n’est pas la bonne réponse.'}
                            </Text>
                            <Text style={[styles.description, { color: theme.text }]}>{question.options[revealedAnswer.correct_option]}. {revealedAnswer.explanation}</Text>
                            {session.mode === 'audio' ? (
                                <Text style={[styles.smallHint, { color: theme.text }]}>
                                    {manualAudioPlayback
                                        ? 'Appuie sur « Écouter la correction »; la question suivante démarrera ensuite.'
                                        : 'La réponse est lue automatiquement, puis la question suivante démarre.'}
                                </Text>
                            ) : null}
                        </View>
                    ) : null}
                </>
            ) : null}
            {session.status === 'paused' ? <Text style={[styles.pauseNotice, { color: theme.primary }]}>Partie en pause — ta progression est sauvegardée.</Text> : null}
            <View style={styles.navigationRow}>
                <Pressable disabled={session.current_index === 0 || busy} onPress={() => void onMove('previous')} style={[styles.secondaryAction, { borderColor: theme.primary }]}>
                    <Text style={[styles.secondaryActionText, { color: theme.primary }]}>← Précédente</Text>
                </Pressable>
                {session.mode === 'audio' ? (
                    <View style={[styles.mainAction, { backgroundColor: theme.accent }]}>
                        <Text style={styles.mainActionText}>
                            {answer
                                ? manualAudioPlayback ? 'Écoute ou passe la correction ci-dessus' : 'Lecture automatique…'
                                : 'Réponds avant la fin du temps'}
                        </Text>
                    </View>
                ) : (
                    <Pressable disabled={!answer || busy} onPress={() => void onMove('next')} style={[styles.mainAction, { backgroundColor: answer ? theme.primary : theme.accent }]}>
                        <Text style={styles.mainActionText}>Suivante →</Text>
                    </Pressable>
                )}
            </View>
            <Pressable disabled={busy} onPress={() => void onPause()} style={styles.pauseButton}>
                <Text style={[styles.pauseText, { color: theme.primary }]}>{session.status === 'paused' ? '▶ Reprendre la partie' : 'Ⅱ Mettre en pause et sauvegarder'}</Text>
            </Pressable>
        </>
    );
}

function renderChallenge(
    challenge: QuizChallenge,
    theme: ReturnType<typeof useTheme>,
    remaining: number,
    onAnswer: (optionIndex: number) => Promise<void>,
    onAction: (challenge: QuizChallenge, action: 'accept' | 'decline' | 'pause' | 'resume' | 'quit' | 'rematch') => Promise<void>,
    busy: boolean,
) {
    if (challenge.status === 'pending') {
        if (!challenge.is_incoming) {
            return (
                <View>
                    <Text style={[styles.heading, { color: theme.text }]}>Défi envoyé</Text>
                    <Text style={[styles.description, { color: theme.text }]}>En attente de la réponse de {opponentLabel(challenge.opponent)}.</Text>
                </View>
            );
        }
        return (
            <View>
                <Text style={[styles.heading, { color: theme.text }]}>⚔️ Défi de {opponentLabel(challenge.opponent)}</Text>
                <Text style={[styles.description, { color: theme.text }]}>Accepte le défi de {opponentLabel(challenge.opponent)} pour répondre aux mêmes questions en 90 secondes.</Text>
                <View style={styles.navigationRow}>
                    <Pressable disabled={busy} onPress={() => void onAction(challenge, 'decline')} style={[styles.secondaryAction, { borderColor: theme.primary }]}>
                        <Text style={[styles.secondaryActionText, { color: theme.primary }]}>Refuser</Text>
                    </Pressable>
                    <Pressable disabled={busy} onPress={() => void onAction(challenge, 'accept')} style={[styles.mainAction, { backgroundColor: theme.primary }]}>
                        <Text style={styles.mainActionText}>Accepter</Text>
                    </Pressable>
                </View>
            </View>
        );
    }
    if (challenge.status === 'completed' || challenge.status === 'expired') {
        const outcome = challenge.result?.outcome;
        const result = outcome === 'won'
            ? { title: 'Tu as gagné le défi !', icon: '🏆', detail: 'Belle victoire !' }
            : outcome === 'draw'
                ? { title: 'Match nul !', icon: '🤝', detail: 'Vous avez terminé à égalité.' }
                : outcome === 'lost'
                    ? { title: 'Tu as perdu le défi.', icon: '📖', detail: 'Ton adversaire a gagné cette fois.' }
                    : { title: 'Défi terminé', icon: '📖', detail: 'Le résultat détaillé n’est pas disponible.' };
        return (
            <View style={styles.result}>
                <Text style={styles.resultIcon}>{result.icon}</Text>
                <Text style={[styles.heading, { color: theme.text }]}>{result.title}</Text>
                <Text style={[styles.description, { color: theme.text }]}>{result.detail}</Text>
                <Text style={[styles.description, { color: theme.text }]}>Score : {challenge.my_score ?? 0} à {challenge.opponent_score ?? 0}</Text>
                <Pressable disabled={busy} onPress={() => void onAction(challenge, 'rematch')} style={[styles.mainAction, { backgroundColor: theme.primary }]}>
                    <Text style={styles.mainActionText}>↻ Demander la revanche</Text>
                </Pressable>
            </View>
        );
    }
    if (challenge.status === 'declined') {
        return (
            <View>
                <Text style={[styles.heading, { color: theme.text }]}>Défi refusé</Text>
                <Text style={[styles.description, { color: theme.text }]}>
                    {opponentLabel(challenge.opponent)} a refusé cette invitation. Vous pouvez proposer un nouveau défi.
                </Text>
                <Pressable disabled={busy} onPress={() => void onAction(challenge, 'rematch')} style={[styles.mainAction, { backgroundColor: theme.primary }]}>
                    <Text style={styles.mainActionText}>Proposer un nouveau défi</Text>
                </Pressable>
            </View>
        );
    }
    return (
        <>
            <Text style={[styles.heading, { color: theme.text }]}>Défi contre {opponentLabel(challenge.opponent)}</Text>
            <View style={styles.gameTopRow}>
                <Text style={[styles.progress, { color: theme.text }]}>Question {Math.min(challenge.current_index + 1, challenge.total_questions ?? 10)} / {challenge.total_questions ?? 10}</Text>
                <Text style={[styles.timer, { color: remaining <= 15 ? '#b42318' : theme.primary }]}>⏱ {formatTime(remaining)}</Text>
            </View>
            <View style={[styles.progressTrack, { backgroundColor: theme.accent }]}>
                <View style={[styles.progressFill, { width: `${(Math.min(challenge.current_index + 1, challenge.total_questions ?? 10) / (challenge.total_questions ?? 10)) * 100}%`, backgroundColor: theme.primary }]} />
            </View>
            {challenge.current_question ? (
                <>
                    <Text style={[styles.category, { color: theme.primary }]}>{challenge.current_question.category}</Text>
                    <Text style={[styles.question, { color: theme.text }]}>{challenge.current_question.prompt}</Text>
                    <View style={styles.options}>
                        {challenge.current_question.options.map((option, index) => (
                            <Pressable key={`${challenge.current_question?.id}-${index}`} disabled={busy || challenge.status !== 'active' || challenge.is_paused} onPress={() => void onAnswer(index)} style={[styles.option, { borderColor: theme.accent, backgroundColor: theme.background }]}>
                                <Text style={[styles.optionLetter, { backgroundColor: theme.primary }]}>{String.fromCharCode(65 + index)}</Text>
                                <Text style={[styles.optionText, { color: theme.text }]}>{option}</Text>
                            </Pressable>
                        ))}
                    </View>
                </>
            ) : <Text style={[styles.description, { color: theme.text }]}>En attente de ton adversaire…</Text>}
            <Text style={[styles.smallHint, { color: theme.text }]}>Réponds aux 10 questions en 90 secondes. Le score reste masqué jusqu’à la fin des deux manches.</Text>
            {challenge.current_index < (challenge.total_questions ?? 10) ? (
                <>
                    <Pressable disabled={busy || challenge.current_index >= (challenge.total_questions ?? 10)} onPress={() => void onAction(challenge, challenge.is_paused ? 'resume' : 'pause')} style={styles.pauseButton}>
                        <Text style={[styles.pauseText, { color: theme.primary }]}>{challenge.is_paused ? '▶ Reprendre le défi' : 'Ⅱ Mettre en pause'}</Text>
                    </Pressable>
                    <Pressable disabled={busy} onPress={() => void onAction(challenge, 'quit')} style={styles.pauseButton}>
                        <Text style={[styles.pauseText, { color: theme.primary }]}>Enregistrer et quitter</Text>
                    </Pressable>
                </>
            ) : null}
        </>
    );
}

function ChallengeRow({
    challenge,
    theme,
    onOpen,
    onAction,
    busy,
}: {
    challenge: QuizChallenge;
    theme: ReturnType<typeof useTheme>;
    onOpen: () => void;
    onAction: (action: 'accept' | 'decline' | 'pause' | 'resume' | 'quit' | 'rematch') => void;
    busy: boolean;
}) {
    const statusLabel = challenge.status === 'pending'
        ? challenge.is_incoming ? 'Nouveau défi reçu — à accepter ou refuser' : 'Invitation envoyée — en attente de réponse'
        : challenge.status === 'active'
            ? challenge.is_paused ? 'Défi accepté — en pause' : 'Défi accepté — partie en cours'
            : challenge.status === 'completed' || challenge.status === 'expired' ? 'Terminé'
                : challenge.status === 'declined' ? 'Défi refusé' : 'En attente';
    return (
        <View style={[styles.challengeRow, { backgroundColor: theme.card, borderColor: theme.accent }]}>
            <Pressable onPress={onOpen} style={styles.challengeInfo}>
                <Text style={[styles.contactName, { color: theme.text }]}>{opponentLabel(challenge.opponent)}</Text>
                <Text style={[styles.contactGroup, { color: theme.primary }]}>{statusLabel}</Text>
            </Pressable>
            {challenge.status === 'pending' && challenge.is_incoming ? (
                <View style={styles.challengeActions}>
                    <Pressable disabled={busy} onPress={() => onAction('decline')}>
                        <Text style={[styles.challengeAction, { color: '#b42318' }]}>Refuser</Text>
                    </Pressable>
                    <Pressable disabled={busy} onPress={() => onAction('accept')}>
                        <Text style={[styles.challengeAction, { color: theme.primary }]}>Accepter</Text>
                    </Pressable>
                </View>
            ) : challenge.status === 'pending' ? (
                <Text style={[styles.challengeAction, { color: theme.text }]}>En attente…</Text>
            ) : challenge.status === 'completed' || challenge.status === 'expired' || challenge.status === 'declined' ? (
                <Pressable disabled={busy} onPress={() => onAction('rematch')}><Text style={[styles.challengeAction, { color: theme.primary }]}>Revanche</Text></Pressable>
            ) : (
                <Pressable onPress={onOpen}><Text style={[styles.challengeAction, { color: theme.primary }]}>{challenge.is_paused ? 'Reprendre →' : 'Jouer →'}</Text></Pressable>
            )}
        </View>
    );
}

const styles = StyleSheet.create({
    container: { flexGrow: 1, width: '100%', alignSelf: 'center', paddingVertical: 24 },
    hero: { flexDirection: 'row', alignItems: 'center', gap: 16, borderRadius: 18, padding: 22, marginBottom: 18 },
    heroIcon: { fontSize: 44 },
    heroCopy: { flex: 1 },
    heroTitle: { color: '#fff', fontSize: 22, fontWeight: '800', marginBottom: 5 },
    heroText: { color: '#fff', fontSize: 14, lineHeight: 20 },
    modePicker: { flexDirection: 'row', borderWidth: 1, borderRadius: 12, overflow: 'hidden', marginBottom: 18 },
    modeButton: { flex: 1, minHeight: 44, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 8 },
    modeButtonText: { fontSize: 14, fontWeight: '700' },
    content: { width: '100%' },
    card: { borderWidth: 1, borderRadius: 18, padding: 20, marginBottom: 20 },
    heading: { fontSize: 20, fontWeight: '800', marginBottom: 10 },
    description: { fontSize: 14, lineHeight: 21, marginBottom: 14 },
    choiceRow: { flexDirection: 'row', gap: 12, marginTop: 10 },
    choiceCard: { flex: 1, minHeight: 160, borderWidth: 1, borderRadius: 16, padding: 16, justifyContent: 'center', alignItems: 'center' },
    choiceIcon: { fontSize: 34, marginBottom: 8 },
    choiceTitle: { fontSize: 16, fontWeight: '800', textAlign: 'center' },
    choiceHint: { fontSize: 12, textAlign: 'center', opacity: 0.75, marginTop: 5 },
    resumeButton: { borderWidth: 1, borderRadius: 10, padding: 13, alignItems: 'center', marginTop: 16 },
    resumeText: { fontWeight: '700' },
    error: { color: '#b42318', backgroundColor: '#fff0ed', borderRadius: 10, padding: 12, marginBottom: 12 },
    gameTopRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 8, marginBottom: 8 },
    progress: { fontWeight: '700', fontSize: 14 },
    timer: { fontSize: 18, fontWeight: '900' },
    progressTrack: { height: 7, borderRadius: 5, overflow: 'hidden', marginBottom: 18 },
    progressFill: { height: '100%', borderRadius: 5 },
    category: { fontSize: 12, fontWeight: '800', textTransform: 'uppercase', marginBottom: 8 },
    question: { fontSize: 21, fontWeight: '800', lineHeight: 29, marginBottom: 18 },
    options: { gap: 10 },
    option: { minHeight: 54, flexDirection: 'row', alignItems: 'center', borderWidth: 1, borderRadius: 12, padding: 10 },
    optionLetter: { width: 30, height: 30, borderRadius: 15, color: '#fff', textAlign: 'center', textAlignVertical: 'center', fontWeight: '800', marginRight: 10, overflow: 'hidden', paddingTop: 5 },
    optionText: { flex: 1, fontSize: 15, lineHeight: 20 },
    correctOption: { borderColor: '#198754', backgroundColor: '#eaf7ef' },
    wrongOption: { borderColor: '#b42318', backgroundColor: '#fff0ed' },
    explanation: { borderWidth: 1, borderRadius: 12, padding: 14, marginTop: 16 },
    answerFeedback: { fontSize: 15, fontWeight: '800', marginBottom: 6 },
    smallHint: { fontSize: 12, opacity: 0.72, lineHeight: 17, marginTop: 8 },
    navigationRow: { flexDirection: 'row', gap: 10, marginTop: 20 },
    mainAction: { flex: 1, minHeight: 44, borderRadius: 10, justifyContent: 'center', alignItems: 'center', paddingHorizontal: 12 },
    mainActionText: { color: '#fff', fontSize: 14, fontWeight: '800', textAlign: 'center' },
    secondaryAction: { flex: 1, minHeight: 44, borderWidth: 1, borderRadius: 10, justifyContent: 'center', alignItems: 'center', paddingHorizontal: 10 },
    secondaryActionText: { fontSize: 14, fontWeight: '700' },
    pauseButton: { paddingVertical: 14, alignItems: 'center' },
    pauseText: { fontWeight: '700', fontSize: 14 },
    audioAction: { alignSelf: 'flex-start', borderWidth: 1, borderRadius: 10, paddingVertical: 10, paddingHorizontal: 14, marginBottom: 14 },
    audioActionText: { fontSize: 14, fontWeight: '700' },
    pauseNotice: { fontWeight: '800', textAlign: 'center', padding: 12 },
    result: { alignItems: 'center', paddingVertical: 18 },
    resultIcon: { fontSize: 58, marginBottom: 10 },
    back: { fontWeight: '700', marginBottom: 14 },
    contactList: { gap: 10 },
    contactCard: { flexDirection: 'row', alignItems: 'center', borderWidth: 1, borderRadius: 12, padding: 12 },
    contactIcon: { fontSize: 28, marginRight: 10 },
    contactCopy: { flex: 1 },
    contactName: { fontSize: 15, fontWeight: '700' },
    contactGroup: { fontSize: 12, marginTop: 3 },
    challengeAction: { fontSize: 13, fontWeight: '800' },
    challengeTabs: { flexDirection: 'row', borderWidth: 1, borderRadius: 12, overflow: 'hidden', marginBottom: 12 },
    challengeTab: { flex: 1, minHeight: 44, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 8 },
    challengeTabText: { fontSize: 14, fontWeight: '700' },
    challengeRow: { flexDirection: 'row', alignItems: 'center', borderWidth: 1, borderRadius: 12, padding: 13, marginBottom: 8 },
    challengeInfo: { flex: 1 },
    challengeActions: { flexDirection: 'row', alignItems: 'center', gap: 12, marginLeft: 8 },
});
