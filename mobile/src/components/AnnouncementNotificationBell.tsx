import React, { useCallback, useMemo, useRef, useState } from 'react';
import {
    ActivityIndicator,
    AppState,
    Modal,
    Pressable,
    ScrollView,
    StyleSheet,
    Text,
    View,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useFocusEffect, useNavigation } from '@react-navigation/native';
import Svg, { Path } from 'react-native-svg';
import apiClient from '../api/apiClient';
import { getToken } from '../api/tokenStorage';
import { Announcement } from '../types/Announcement';
import type { RootStackParamList } from '../navigation/AppNavigator';
import {
    fetchQuizNotifications,
    markQuizNotificationRead,
    QuizNotification,
} from '../api/quizService';
import {
    fetchParishNotifications,
    markAllParishNotificationsRead,
    markParishNotificationRead,
    ParishNotification,
} from '../api/notificationService';
import { useTheme } from '../theme/LiturgicalTheme';

type NotificationCursor = {
    publishedAt: string;
    id: number;
};

type Props = {
    compact?: boolean;
};

const CURSOR_STORAGE_KEY = 'announcementsNotificationCursor';
const POLL_INTERVAL_MS = 60_000;
const NOTIFICATION_POLL_INTERVAL_MS = 10_000;

function getCursor(announcements: Announcement[]): NotificationCursor | null {
    return announcements.reduce<NotificationCursor | null>((latest, announcement) => {
        const publishedAt = announcement.published_at || announcement.created_at;
        const id = Number(announcement.id);
        if (!publishedAt || !Number.isFinite(id)) return latest;

        const candidate = { publishedAt, id };
        if (
            !latest ||
            candidate.publishedAt > latest.publishedAt ||
            (candidate.publishedAt === latest.publishedAt && candidate.id > latest.id)
        ) {
            return candidate;
        }
        return latest;
    }, null);
}

function isAfterCursor(announcement: Announcement, cursor: NotificationCursor) {
    const publishedAt = announcement.published_at || announcement.created_at;
    const id = Number(announcement.id);
    if (!publishedAt || !Number.isFinite(id)) return false;
    return publishedAt > cursor.publishedAt || (publishedAt === cursor.publishedAt && id > cursor.id);
}

export default function AnnouncementNotificationBell({ compact = false }: Props) {
    const theme = useTheme();
    const navigation = useNavigation<NativeStackNavigationProp<RootStackParamList>>();
    const [announcements, setAnnouncements] = useState<Announcement[]>([]);
    const [quizNotifications, setQuizNotifications] = useState<QuizNotification[]>([]);
    const [parishNotifications, setParishNotifications] = useState<ParishNotification[]>([]);
    const [cursor, setCursor] = useState<NotificationCursor | null>(null);
    const [initialized, setInitialized] = useState(false);
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [visible, setVisible] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [quizError, setQuizError] = useState('');
    const [parishNotificationError, setParishNotificationError] = useState('');
    const polling = useRef(false);
    const notificationPolling = useRef(false);

    const newAnnouncements = useMemo(
        () => initialized
            ? cursor
                ? announcements.filter((announcement) => isAfterCursor(announcement, cursor))
                : announcements
            : [],
        [announcements, cursor, initialized],
    );
    const unreadQuizNotifications = useMemo(
        () => quizNotifications.filter((notification) => !notification.is_read),
        [quizNotifications],
    );
    const unreadCount = newAnnouncements.length
        + unreadQuizNotifications.length
        + parishNotifications.length;

    const checkAnnouncements = useCallback(async () => {
        if (polling.current) return;
        polling.current = true;
        setLoading(true);
        try {
            const [response, storedCursor] = await Promise.all([
                apiClient.get<Announcement[]>('/annonces/'),
                AsyncStorage.getItem(CURSOR_STORAGE_KEY),
            ]);
            const items: Announcement[] = response.data;
            setAnnouncements(items);

            if (storedCursor === null) {
                const initialCursor = getCursor(items);
                await AsyncStorage.setItem(CURSOR_STORAGE_KEY, JSON.stringify(initialCursor));
                setCursor(initialCursor);
                setInitialized(true);
            } else {
                setCursor(JSON.parse(storedCursor) as NotificationCursor);
                setInitialized(true);
            }
            setError('');
        } catch {
            setError('Les notifications sont momentanément indisponibles.');
        } finally {
            polling.current = false;
            setLoading(false);
        }
    }, []);

    const checkNotifications = useCallback(async () => {
        if (notificationPolling.current) return;
        notificationPolling.current = true;
        try {
            const [quizResult, parishResult] = await Promise.allSettled([
                fetchQuizNotifications(),
                fetchParishNotifications(),
            ]);
            if (quizResult.status === 'fulfilled') {
                setQuizNotifications(quizResult.value);
                setQuizError('');
            } else {
                setQuizError('Les notifications de défis sont momentanément indisponibles.');
            }
            if (parishResult.status === 'fulfilled') {
                setParishNotifications(parishResult.value);
                setParishNotificationError('');
            } else {
                setParishNotificationError('Les notifications paroissiales sont momentanément indisponibles.');
            }
        } finally {
            notificationPolling.current = false;
        }
    }, []);

    useFocusEffect(useCallback(() => {
        let active = true;
        let announcementInterval: ReturnType<typeof setInterval> | undefined;
        let notificationInterval: ReturnType<typeof setInterval> | undefined;
        let subscription: ReturnType<typeof AppState.addEventListener> | undefined;

        const syncAuthentication = async () => {
            let token: string | null;
            try {
                token = await getToken();
            } catch {
                if (active) setIsAuthenticated(false);
                return;
            }
            if (!active) return;

            const authenticated = Boolean(token);
            setIsAuthenticated(authenticated);
            if (!authenticated) {
                setAnnouncements([]);
                setQuizNotifications([]);
                setParishNotifications([]);
                setCursor(null);
                setInitialized(false);
                setVisible(false);
                setError('');
                setQuizError('');
                setParishNotificationError('');
                return;
            }

            void checkAnnouncements();
            void checkNotifications();
            announcementInterval = setInterval(() => {
                if (AppState.currentState === 'active') {
                    void checkAnnouncements();
                }
            }, POLL_INTERVAL_MS);
            notificationInterval = setInterval(() => {
                if (AppState.currentState === 'active') {
                    void checkNotifications();
                }
            }, NOTIFICATION_POLL_INTERVAL_MS);
            subscription = AppState.addEventListener('change', (state) => {
                if (state === 'active') {
                    void checkAnnouncements();
                    void checkNotifications();
                }
            });
        };

        void syncAuthentication();

        return () => {
            active = false;
            if (announcementInterval) clearInterval(announcementInterval);
            if (notificationInterval) clearInterval(notificationInterval);
            subscription?.remove();
        };
    }, [checkAnnouncements, checkNotifications]));

    const markAnnouncementsAsRead = async () => {
        const latestCursor = getCursor(announcements);
        if (latestCursor) {
            try {
                await AsyncStorage.setItem(CURSOR_STORAGE_KEY, JSON.stringify(latestCursor));
                setCursor(latestCursor);
            } catch {
                setError('Impossible d’enregistrer la lecture des annonces.');
            }
        }
    };

    const markNotificationsAsRead = async () => {
        await markAnnouncementsAsRead();
        try {
            const unread = quizNotifications.filter((notification) => !notification.is_read);
            const updated = await Promise.all(
                unread.map((notification) => markQuizNotificationRead(notification.id)),
            );
            setQuizNotifications((current) => current.map((notification) => {
                const read = updated.find((item) => item.id === notification.id);
                return read || notification;
            }));
        } catch {
            setQuizError('Impossible de marquer les notifications de défis comme lues.');
        }
        try {
            await markAllParishNotificationsRead();
            setParishNotifications([]);
            setParishNotificationError('');
        } catch {
            setParishNotificationError('Impossible de marquer les notifications comme lues.');
        }
        setVisible(false);
    };

    const openAnnouncement = async (announcement: Announcement) => {
        await markAnnouncementsAsRead();
        setVisible(false);
        navigation.navigate('AnnouncementDetail', { announcement });
    };

    const openQuizNotification = async (notification: QuizNotification) => {
        try {
            await markQuizNotificationRead(notification.id);
            setQuizNotifications((current) => current.map((item) =>
                item.id === notification.id ? { ...item, is_read: true } : item,
            ));
        } catch {
            setQuizError('La notification n’a pas pu être marquée comme lue.');
        }
        setVisible(false);
        navigation.navigate('SpiritualGame', { challengeId: notification.challenge_id });
    };

    const openParishNotification = async (notification: ParishNotification) => {
        try {
            await markParishNotificationRead(notification.id);
            setParishNotifications((current) => current.filter((item) => item.id !== notification.id));
            setParishNotificationError('');
        } catch {
            setParishNotificationError('La notification n’a pas pu être marquée comme lue.');
        }
        setVisible(false);
        navigation.navigate('MassRequests');
    };

    if (!isAuthenticated) return null;

    return (
        <>
            <Pressable
                accessibilityRole="button"
                accessibilityLabel={`Notifications${unreadCount ? `, ${unreadCount} nouvelle(s)` : ''}`}
                onPress={() => setVisible(true)}
                style={[styles.bellButton, compact && styles.compactBellButton]}
            >
                <Svg
                    width={compact ? 21 : 24}
                    height={compact ? 21 : 24}
                    viewBox="0 0 24 24"
                    fill="none"
                >
                    <Path
                        d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"
                        stroke={getHeaderTintColor(theme.primary)}
                        strokeWidth={1.8}
                        strokeLinecap="round"
                        strokeLinejoin="round"
                    />
                </Svg>
                {unreadCount > 0 ? (
                    <View style={styles.badge}>
                        <Text style={styles.badgeText}>
                            {unreadCount > 99 ? '99+' : unreadCount}
                        </Text>
                    </View>
                ) : null}
            </Pressable>

            <Modal
                visible={visible}
                transparent
                animationType="fade"
                onRequestClose={() => void markNotificationsAsRead()}
            >
                <View style={styles.backdrop}>
                    <Pressable
                        accessibilityRole="button"
                        accessibilityLabel="Fermer les notifications"
                        style={StyleSheet.absoluteFill}
                        onPress={() => void markNotificationsAsRead()}
                    />
                    <View style={[styles.panel, { backgroundColor: theme.card, borderColor: theme.accent }]}>
                        <View style={styles.panelHeader}>
                            <Text style={[styles.title, { color: theme.text }]}>Notifications</Text>
                            <Pressable
                                accessibilityRole="button"
                                accessibilityLabel="Fermer les notifications"
                                onPress={() => void markNotificationsAsRead()}
                            >
                                <Text style={[styles.close, { color: theme.primary }]}>Fermer</Text>
                            </Pressable>
                        </View>
                        {loading && announcements.length === 0 ? (
                            <ActivityIndicator color={theme.primary} />
                        ) : null}
                        {error ? <Text style={styles.error}>{error}</Text> : null}
                        {quizError ? <Text style={styles.error}>{quizError}</Text> : null}
                        {parishNotificationError ? <Text style={styles.error}>{parishNotificationError}</Text> : null}
                        {!loading && unreadCount === 0 ? (
                            <Text style={[styles.empty, { color: theme.text }]}>Aucune nouvelle notification.</Text>
                        ) : (
                            <ScrollView style={styles.list}>
                                {unreadQuizNotifications.map((notification) => (
                                    <Pressable
                                        key={`quiz-${notification.id}`}
                                        accessibilityRole="button"
                                        onPress={() => void openQuizNotification(notification)}
                                        style={[styles.item, { borderBottomColor: theme.accent }]}
                                    >
                                        <View style={styles.itemHeader}>
                                            <View style={styles.unreadDot} />
                                            <Text style={[styles.itemTitle, { color: theme.text }]}>
                                                {notification.kind === 'invitation'
                                                    ? '⚔️ Défi biblique reçu'
                                                    : notification.kind === 'accepted'
                                                        ? '⚔️ Défi accepté'
                                                        : '⚔️ Défi refusé'}
                                            </Text>
                                        </View>
                                        <Text style={[styles.itemBody, { color: theme.text }]}>
                                            {notification.message} Appuyez pour ouvrir le défi.
                                        </Text>
                                        <Text style={[styles.date, { color: theme.text }]}>
                                            {new Date(notification.created_at).toLocaleDateString('fr-FR')}
                                        </Text>
                                    </Pressable>
                                ))}
                                {parishNotifications.map((notification) => (
                                    <Pressable
                                        key={`parish-${notification.id}`}
                                        accessibilityRole="button"
                                        accessibilityLabel={notification.title}
                                        onPress={() => void openParishNotification(notification)}
                                        style={[styles.item, { borderBottomColor: theme.accent }]}
                                    >
                                        <View style={styles.itemHeader}>
                                            <View style={styles.unreadDot} />
                                            <Text style={[styles.itemTitle, { color: theme.text }]}>
                                                {notification.title}
                                            </Text>
                                        </View>
                                        <Text style={[styles.itemBody, { color: theme.text }]} numberOfLines={2}>
                                            {notification.message}
                                        </Text>
                                        <Text style={[styles.date, { color: theme.text }]}>
                                            {new Date(notification.created_at).toLocaleDateString('fr-FR')}
                                        </Text>
                                    </Pressable>
                                ))}
                                {newAnnouncements.map((announcement) => (
                                    <Pressable
                                        key={announcement.id}
                                        accessibilityRole="button"
                                        onPress={() => void openAnnouncement(announcement)}
                                        style={[styles.item, { borderBottomColor: theme.accent }]}
                                    >
                                        <View style={styles.itemHeader}>
                                            <View style={styles.unreadDot} />
                                            <Text style={[styles.itemTitle, { color: theme.text }]}>
                                                {announcement.title}
                                            </Text>
                                        </View>
                                        <Text style={[styles.itemBody, { color: theme.text }]} numberOfLines={2}>
                                            {announcement.body}
                                        </Text>
                                        {announcement.published_at ? (
                                            <Text style={[styles.date, { color: theme.text }]}>
                                                {new Date(announcement.published_at).toLocaleDateString('fr-FR')}
                                            </Text>
                                        ) : null}
                                    </Pressable>
                                ))}
                            </ScrollView>
                        )}
                        {unreadCount > 0 ? (
                            <Pressable
                                accessibilityRole="button"
                                onPress={() => void markNotificationsAsRead()}
                                style={[styles.readButton, { backgroundColor: theme.primary }]}
                            >
                                <Text style={styles.readButtonText}>Tout marquer comme lu</Text>
                            </Pressable>
                        ) : null}
                    </View>
                </View>
            </Modal>
        </>
    );
}

const styles = StyleSheet.create({
    bellButton: {
        width: 44,
        height: 44,
        marginRight: 8,
        alignItems: 'center',
        justifyContent: 'center',
    },
    compactBellButton: {
        width: 38,
        height: 40,
        marginRight: 4,
    },
    badge: {
        position: 'absolute',
        top: 1,
        right: 0,
        minWidth: 18,
        height: 18,
        paddingHorizontal: 4,
        borderRadius: 9,
        backgroundColor: '#d62828',
        alignItems: 'center',
        justifyContent: 'center',
    },
    badgeText: {
        color: '#fff',
        fontSize: 10,
        fontWeight: '700',
    },
    backdrop: {
        flex: 1,
        justifyContent: 'flex-start',
        alignItems: 'flex-end',
        paddingTop: 56,
        paddingHorizontal: 12,
        backgroundColor: 'rgba(0, 0, 0, 0.35)',
    },
    panel: {
        width: '100%',
        maxWidth: 380,
        maxHeight: '75%',
        padding: 16,
        borderWidth: 1,
        borderRadius: 16,
        shadowColor: '#000',
        shadowOpacity: 0.2,
        shadowOffset: { width: 0, height: 6 },
        shadowRadius: 14,
        elevation: 8,
    },
    panelHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: 12,
    },
    title: {
        fontSize: 18,
        fontWeight: '700',
    },
    close: {
        fontSize: 13,
        fontWeight: '700',
    },
    list: {
        flexShrink: 1,
    },
    item: {
        paddingVertical: 12,
        borderBottomWidth: StyleSheet.hairlineWidth,
    },
    itemHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
    },
    unreadDot: {
        width: 8,
        height: 8,
        borderRadius: 4,
        backgroundColor: '#d62828',
    },
    itemTitle: {
        flex: 1,
        fontSize: 14,
        fontWeight: '700',
    },
    itemBody: {
        marginTop: 5,
        marginLeft: 16,
        fontSize: 13,
        lineHeight: 18,
    },
    date: {
        marginTop: 5,
        marginLeft: 16,
        fontSize: 11,
        opacity: 0.7,
    },
    empty: {
        paddingVertical: 16,
        fontSize: 13,
    },
    error: {
        marginBottom: 8,
        color: '#a33b32',
        fontSize: 12,
    },
    readButton: {
        alignSelf: 'flex-end',
        marginTop: 12,
        paddingHorizontal: 14,
        paddingVertical: 10,
        borderRadius: 9,
    },
    readButtonText: {
        color: '#fff',
        fontSize: 12,
        fontWeight: '700',
    },
});

function getHeaderTintColor(primary: string) {
    const clean = primary.replace('#', '');
    const value = Number.parseInt(clean, 16);
    const channels = [(value >> 16) & 255, (value >> 8) & 255, value & 255].map((channel) => {
        const normalized = channel / 255;
        return normalized <= 0.03928
            ? normalized / 12.92
            : Math.pow((normalized + 0.055) / 1.055, 2.4);
    });
    const luminance = 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
    return luminance > 0.179 ? '#211a16' : '#fff';
}
