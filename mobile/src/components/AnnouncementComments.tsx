import React, { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import apiClient from '../api/apiClient';
import { getToken } from '../api/tokenStorage';
import { getQueuedMutations, sendOrQueue, subscribeOutbox } from '../api/offlineService';
import { readOfflineDraft, writeOfflineDraft } from '../api/offlineStorage';
import { useTheme } from '../theme/LiturgicalTheme';

type AnnouncementComment = {
    id: number;
    author_name: string;
    body: string;
    created_at: string;
    pending?: boolean;
    syncStatus?: 'pending' | 'failed';
};

type Props = {
    announcementId: string;
    onCountChange?: (announcementId: string, count: number) => void;
    onRequestLogin?: () => void;
};

export default function AnnouncementComments({ announcementId, onCountChange, onRequestLogin }: Props) {
    const theme = useTheme();
    const [comments, setComments] = useState<AnnouncementComment[]>([]);
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [comment, setComment] = useState('');
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [message, setMessage] = useState('');
    const [draftReady, setDraftReady] = useState(false);

    useEffect(() => {
        let active = true;
        setDraftReady(false);
        void getToken()
            .then((token) => readOfflineDraft<string>(token, `announcement-comment-${announcementId}`))
            .then((draft) => {
                if (active && draft) setComment(draft);
            })
            .catch((error: unknown) => {
                console.error('Le brouillon du commentaire n’a pas pu être restauré.', error);
            })
            .finally(() => {
                if (active) setDraftReady(true);
            });
        return () => { active = false; };
    }, [announcementId]);

    useEffect(() => {
        if (!draftReady) return undefined;
        const timeout = setTimeout(() => {
            void getToken()
                .then((token) => writeOfflineDraft(
                    token,
                    `announcement-comment-${announcementId}`,
                    comment || null,
                ))
                .catch((error: unknown) => {
                    console.error('Le brouillon du commentaire n’a pas pu être enregistré.', error);
                });
        }, 250);
        return () => clearTimeout(timeout);
    }, [announcementId, comment, draftReady]);

    useEffect(() => {
        let active = true;
        const loadComments = async () => {
            const [commentsResult, tokenResult, queuedResult] = await Promise.allSettled([
                apiClient.get(`/annonces/${announcementId}/commentaires/`),
                getToken(),
                getQueuedMutations(`/annonces/${announcementId}/commentaires/`),
            ]);
            if (!active) return;

            if (tokenResult.status === 'fulfilled') {
                setIsAuthenticated(Boolean(tokenResult.value));
            } else {
                setMessage('Impossible de vérifier votre connexion.');
            }

            const savedComments = commentsResult.status === 'fulfilled'
                ? commentsResult.value.data as AnnouncementComment[]
                : [];
            const pendingComments = queuedResult.status === 'fulfilled'
                ? queuedResult.value.map((mutation, index) => {
                    const data = mutation.data as { body?: string };
                    return {
                        id: -(index + 1),
                        author_name: 'Vous',
                        body: data.body ?? '',
                        created_at: mutation.createdAt,
                        pending: true,
                        syncStatus: mutation.status,
                    };
                })
                : [];
            const visibleComments = [...savedComments, ...pendingComments];
            setComments(visibleComments);
            onCountChange?.(announcementId, visibleComments.length);
            if (commentsResult.status === 'rejected' && queuedResult.status === 'rejected') {
                setMessage('Impossible de charger les commentaires enregistrés sur le serveur ou cet appareil.');
            } else if (commentsResult.status === 'rejected') {
                setMessage('Commentaires du serveur indisponibles. Les actions enregistrées sur cet appareil restent visibles.');
            }
            setLoading(false);
        };
        void loadComments();
        const unsubscribeOutbox = subscribeOutbox(() => { void loadComments(); });
        return () => {
            active = false;
            unsubscribeOutbox();
        };
    }, [announcementId, onCountChange]);

    const submitComment = async () => {
        const body = comment.trim();
        if (!body || submitting) {
            return;
        }
        setSubmitting(true);
        setMessage('');
        try {
            const result = await sendOrQueue<AnnouncementComment>(
                { method: 'post', url: `/annonces/${announcementId}/commentaires/`, data: { body } },
                () => ({
                    id: -Date.now(),
                    author_name: 'Vous',
                    body,
                    created_at: new Date().toISOString(),
                    pending: true,
                }),
            );
            setComments((current) => [...current, {
                ...result.data,
                ...(result.queued ? { pending: true } : {}),
            }]);
            onCountChange?.(announcementId, comments.length + 1);
            setComment('');
            if (result.queued) setMessage('Commentaire enregistré sur cet appareil. Il sera publié au retour du réseau.');
        } catch (error: any) {
            const detail = error?.response?.data?.detail;
            setMessage(typeof detail === 'string' ? detail : 'Impossible de publier le commentaire. Réessayez.');
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <View style={[styles.container, { borderTopColor: theme.accent }]}>
            <Text style={[styles.heading, { color: theme.primary }]}>
                Commentaires ({comments.length})
            </Text>
            {loading ? (
                <ActivityIndicator color={theme.primary} />
            ) : comments.map((item) => (
                <View key={item.id} style={[styles.comment, { backgroundColor: theme.background }]}>
                    <View style={styles.commentMeta}>
                        <Text style={[styles.author, { color: theme.text }]}>
                            {item.author_name}{item.pending
                                ? item.syncStatus === 'failed' ? ' · échec de synchronisation' : ' · en attente'
                                : ''}
                        </Text>
                        <Text style={[styles.date, { color: theme.text }]}>
                            {new Date(item.created_at).toLocaleDateString('fr-FR')}
                        </Text>
                    </View>
                    <Text style={[styles.body, { color: theme.text }]}>{item.body}</Text>
                </View>
            ))}
            {!loading && comments.length === 0 ? (
                <Text style={[styles.empty, { color: theme.text }]}>Aucun commentaire pour le moment.</Text>
            ) : null}
            {isAuthenticated ? (
                <View style={styles.composer}>
                    <TextInput
                        style={[styles.input, { borderColor: theme.accent, color: theme.text }]}
                        value={comment}
                        onChangeText={setComment}
                        placeholder="Écrire un commentaire…"
                        placeholderTextColor="#8a817a"
                        maxLength={2000}
                        multiline
                        accessibilityLabel="Votre commentaire"
                    />
                    <Pressable
                        accessibilityRole="button"
                        disabled={!comment.trim() || submitting}
                        onPress={submitComment}
                        style={[
                            styles.submit,
                            { backgroundColor: theme.primary },
                            (!comment.trim() || submitting) && styles.submitDisabled,
                        ]}
                    >
                        <Text style={styles.submitText}>{submitting ? 'Envoi…' : 'Publier'}</Text>
                    </Pressable>
                </View>
            ) : (
                <Pressable
                    accessibilityRole="button"
                    onPress={onRequestLogin}
                    disabled={!onRequestLogin}
                >
                    <Text style={[styles.signInHint, { color: theme.primary }]}>
                        Connectez-vous avec votre compte paroissial pour commenter →
                    </Text>
                </Pressable>
            )}
            {message ? <Text style={styles.error}>{message}</Text> : null}
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        marginTop: 16,
        paddingTop: 14,
        borderTopWidth: 1,
    },
    heading: {
        marginBottom: 10,
        fontSize: 15,
        fontWeight: '700',
    },
    comment: {
        marginBottom: 8,
        padding: 10,
        borderRadius: 10,
    },
    commentMeta: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        gap: 8,
        marginBottom: 4,
    },
    author: {
        flexShrink: 1,
        fontSize: 12,
        fontWeight: '700',
    },
    date: {
        fontSize: 11,
        opacity: 0.65,
    },
    body: {
        fontSize: 13,
        lineHeight: 19,
    },
    empty: {
        marginBottom: 10,
        fontSize: 12,
    },
    composer: {
        gap: 8,
    },
    input: {
        minHeight: 48,
        maxHeight: 120,
        paddingHorizontal: 12,
        paddingVertical: 10,
        borderWidth: 1,
        borderRadius: 10,
        textAlignVertical: 'top',
    },
    submit: {
        alignSelf: 'flex-end',
        paddingHorizontal: 16,
        paddingVertical: 10,
        borderRadius: 9,
    },
    submitDisabled: {
        opacity: 0.5,
    },
    submitText: {
        color: '#fff',
        fontSize: 13,
        fontWeight: '700',
    },
    signInHint: {
        fontSize: 12,
        fontStyle: 'italic',
    },
    error: {
        marginTop: 8,
        color: '#a33b32',
        fontSize: 12,
    },
});
