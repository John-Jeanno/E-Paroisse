import apiClient from './apiClient';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { getOfflineAccountKey } from './offlineStorage';
import { sendOrQueue } from './offlineService';
import { getToken } from './tokenStorage';

export type QuizQuestion = {
    id: number;
    category: string;
    prompt: string;
    options: string[];
};

type OfflineQuizQuestion = QuizQuestion & {
    testament: 'ancien' | 'nouveau';
    correct_option: number;
    explanation: string;
};

export type QuizAnswer = {
    question_id: number;
    option_index: number;
    is_correct: boolean;
    correct_option: number;
    explanation: string;
    timed_out: boolean;
};

export type QuizSession = {
    id: number;
    mode: 'text' | 'audio';
    status: 'active' | 'paused' | 'completed';
    current_index: number;
    questions: QuizQuestion[];
    current_question: QuizQuestion | null;
    remaining_seconds: number;
    timer_running: boolean;
    correct_count: number;
    answers: QuizAnswer[];
    current_answer?: QuizAnswer | null;
    offline?: boolean;
};

type OfflineQuizState = {
    session: QuizSession;
    clientSessionId: string;
    resultSubmitted: boolean;
};

const OFFLINE_QUIZ_KEY = 'offline-quiz-session-v1';

async function offlineQuizStorageKey() {
    return `${OFFLINE_QUIZ_KEY}:${getOfflineAccountKey(await getToken())}`;
}

async function saveOfflineQuizState(state: OfflineQuizState) {
    await AsyncStorage.setItem(await offlineQuizStorageKey(), JSON.stringify(state));
}

async function readOfflineQuizState(): Promise<OfflineQuizState | null> {
    const stored = await AsyncStorage.getItem(await offlineQuizStorageKey());
    if (!stored) return null;
    return JSON.parse(stored) as OfflineQuizState;
}

function getLocalAnswer(session: QuizSession, questionId: number) {
    return session.answers.find((answer) => answer.question_id === questionId);
}

async function submitOfflineQuizResult(state: OfflineQuizState) {
    if (state.resultSubmitted) return state;
    const answers = state.session.answers.map((answer) => ({
        question_id: answer.question_id,
        option_index: answer.option_index,
        timed_out: answer.timed_out,
    }));
    await sendOrQueue(
        {
            method: 'post',
            url: '/quiz/offline-results/',
            data: { client_session_id: state.clientSessionId, answers },
        },
        () => ({ client_session_id: state.clientSessionId, queued: true }),
    );
    const updated = { ...state, resultSubmitted: true };
    await saveOfflineQuizState(updated);
    return updated;
}

export async function createOfflineQuizSession(): Promise<QuizSession> {
    const response = await apiClient.get<OfflineQuizQuestion[]>('/quiz/offline-pack/');
    if (response.data.length < 10) {
        throw new Error('Le quiz hors ligne n’est pas encore téléchargé. Connectez-vous pour le préparer.');
    }
    const questions = [...response.data]
        .sort(() => Math.random() - 0.5)
        .slice(0, 10);
    if (questions.some((question) => !Number.isInteger(question.correct_option))) {
        throw new Error('Le pack de questions hors ligne est incomplet. Reconnectez-vous pour le télécharger.');
    }
    const clientSessionId = `local-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
    const session: QuizSession = {
        id: -Date.now(),
        mode: 'text',
        offline: true,
        status: 'active',
        current_index: 0,
        questions,
        current_question: questions[0],
        remaining_seconds: 40,
        timer_running: false,
        correct_count: 0,
        answers: [],
    };
    await saveOfflineQuizState({ session, clientSessionId, resultSubmitted: false });
    return session;
}

export type QuizOpponent = {
    profile_id: number;
    first_name: string;
    last_name: string;
    group_name?: string;
};

export type QuizChallengeResult = {
    scores: { profile_id: number; score: number }[];
    winner_profile_id: number | null;
    is_tie: boolean;
    outcome: 'won' | 'lost' | 'draw';
};

export type QuizNotification = {
    id: number;
    kind: 'invitation' | 'accepted' | 'declined';
    challenge_id: number;
    actor_name: string;
    message: string;
    challenge_status: QuizChallenge['status'];
    is_read: boolean;
    created_at: string;
};

export type QuizChallenge = {
    id: number;
    status: 'pending' | 'active' | 'paused' | 'completed' | 'expired' | 'declined';
    opponent: QuizOpponent;
    is_incoming?: boolean;
    is_paused?: boolean;
    total_questions?: number;
    questions?: QuizQuestion[];
    current_index: number;
    current_question?: QuizQuestion | null;
    remaining_seconds: number | null;
    my_score?: number;
    opponent_score?: number;
    result?: QuizChallengeResult | null;
    my_responses?: QuizAnswer[];
};

export async function createQuizSession(mode: 'text' | 'audio') {
    const response = await apiClient.post<QuizSession>('/quiz/sessions/', {
        mode,
        wait_for_audio_completion: mode === 'audio',
    });
    return response.data;
}

export async function fetchQuizSession(id: number) {
    if (id < 0) {
        const state = await readOfflineQuizState();
        if (!state || state.session.id !== id) {
            throw new Error('Cette partie hors ligne n’existe plus pour ce compte.');
        }
        if (state.session.status === 'completed') await submitOfflineQuizResult(state);
        return state.session;
    }
    const response = await apiClient.get<QuizSession>(`/quiz/sessions/${id}/`);
    return response.data;
}

export async function startQuizQuestionTimer(id: number) {
    const response = await apiClient.post<QuizSession>(`/quiz/sessions/${id}/start/`);
    return response.data;
}

export function getQuizSpeechUrl(id: number, questionId: number, segment: 'question' | 'answer') {
    return apiClient.getUri({
        url: `/quiz/sessions/${id}/speech/`,
        params: { question_id: questionId, segment },
    });
}

export async function answerQuizQuestion(id: number, questionId: number, optionIndex: number) {
    if (id < 0) {
        const state = await readOfflineQuizState();
        if (!state || state.session.id !== id) {
            throw new Error('Cette partie hors ligne n’existe plus pour ce compte.');
        }
        const question = state.session.questions.find((item) => item.id === questionId) as OfflineQuizQuestion | undefined;
        if (!question || state.session.current_question?.id !== questionId) {
            throw new Error('Cette question n’est pas actuellement affichée.');
        }
        if (!Number.isInteger(optionIndex) || optionIndex < 0 || optionIndex >= question.options.length) {
            throw new Error('Ce choix de réponse n’existe pas.');
        }
        if (getLocalAnswer(state.session, questionId)) return state.session;
        const answer: QuizAnswer = {
            question_id: questionId,
            option_index: optionIndex,
            is_correct: optionIndex === question.correct_option,
            correct_option: question.correct_option,
            explanation: question.explanation,
            timed_out: false,
        };
        const updatedSession = {
            ...state.session,
            correct_count: state.session.correct_count + Number(answer.is_correct),
            answers: [...state.session.answers, answer],
        };
        await saveOfflineQuizState({ ...state, session: updatedSession });
        return updatedSession;
    }
    await apiClient.post(`/quiz/sessions/${id}/answer/`, {
        question_id: questionId,
        option_index: optionIndex,
    });
    return fetchQuizSession(id);
}

export async function moveQuizQuestion(id: number, direction: 'next' | 'previous') {
    if (id < 0) {
        let state = await readOfflineQuizState();
        if (!state || state.session.id !== id) {
            throw new Error('Cette partie hors ligne n’existe plus pour ce compte.');
        }
        const currentIndex = state.session.current_index;
        const currentQuestion = state.session.questions[currentIndex];
        if (direction === 'next' && currentQuestion && !getLocalAnswer(state.session, currentQuestion.id)) {
            throw new Error('Répondez à cette question avant de continuer.');
        }
        const nextIndex = direction === 'next'
            ? currentIndex + 1
            : Math.max(0, currentIndex - 1);
        const completed = nextIndex >= state.session.questions.length;
        const updatedSession: QuizSession = {
            ...state.session,
            current_index: completed ? currentIndex : nextIndex,
            current_question: completed ? null : state.session.questions[nextIndex],
            status: completed ? 'completed' : 'active',
            remaining_seconds: 40,
            timer_running: false,
        };
        state = { ...state, session: updatedSession };
        await saveOfflineQuizState(state);
        if (completed) await submitOfflineQuizResult(state);
        return updatedSession;
    }
    const response = await apiClient.post<QuizSession>(`/quiz/sessions/${id}/${direction}/`);
    return response.data;
}

export async function updateQuizSessionPause(id: number, action: 'pause' | 'resume') {
    const response = await apiClient.post<QuizSession>(`/quiz/sessions/${id}/${action}/`);
    return response.data;
}

export async function fetchQuizChallenges() {
    const response = await apiClient.get<QuizChallenge[]>('/quiz/challenges/');
    return response.data;
}

export async function fetchQuizNotifications() {
    const response = await apiClient.get<QuizNotification[]>('/quiz/notifications/');
    return response.data;
}

export async function markQuizNotificationRead(id: number) {
    const response = await apiClient.post<QuizNotification>(`/quiz/notifications/${id}/read/`);
    return response.data;
}

export async function createQuizChallenge(recipientProfileId: number) {
    const response = await apiClient.post<QuizChallenge>('/quiz/challenges/', {
        recipient_profile_id: recipientProfileId,
    });
    return response.data;
}

export async function fetchQuizChallenge(id: number) {
    const response = await apiClient.get<QuizChallenge>(`/quiz/challenges/${id}/`);
    return response.data;
}

export async function updateQuizChallenge(id: number, action: 'accept' | 'decline' | 'pause' | 'resume' | 'quit' | 'rematch') {
    const response = await apiClient.post<QuizChallenge>(`/quiz/challenges/${id}/${action}/`);
    return response.data;
}

export async function answerQuizChallenge(id: number, questionId: number, optionIndex: number) {
    const response = await apiClient.post<QuizChallenge>(`/quiz/challenges/${id}/answer/`, {
        question_id: questionId,
        option_index: optionIndex,
    });
    return response.data;
}
