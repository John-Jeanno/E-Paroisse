import React, { useCallback, useEffect, useState } from 'react';
import { Pressable, Share, StyleSheet, Text, View } from 'react-native';
import apiClient from '../api/apiClient';
import { getQueuedMutations, sendOrQueue, subscribeOutbox } from '../api/offlineService';
import { Announcement } from '../types/Announcement';
import { useTheme } from '../theme/LiturgicalTheme';

type Props = {
    announcement: Announcement;
    commentsCount?: number;
    onCommentsPress?: () => void;
};

export default function AnnouncementEngagement({ announcement, commentsCount, onCommentsPress }: Props) {
    const theme = useTheme();
    const [liked, setLiked] = useState(announcement.is_liked ?? false);
    const [likesCount, setLikesCount] = useState(announcement.likes_count ?? 0);
    const [sharesCount, setSharesCount] = useState(announcement.shares_count ?? 0);
    const [busy, setBusy] = useState<'like' | 'share' | null>(null);
    const [message, setMessage] = useState('');

    const refreshEngagement = useCallback(async () => {
        const [announcementResult, queuedResult] = await Promise.allSettled([
            apiClient.get<Announcement>(`/annonces/${announcement.id}/`),
            getQueuedMutations(`/annonces/${announcement.id}/`),
        ]);
        if (announcementResult.status === 'rejected') {
            console.warn('Impossible d’actualiser les réactions de cette publication.', announcementResult.reason);
        }
        const current = announcementResult.status === 'fulfilled'
            ? announcementResult.value.data
            : announcement;
        const mutations = queuedResult.status === 'fulfilled' ? queuedResult.value : [];
        const pendingLike = mutations
            .filter((mutation) => mutation.url.endsWith('/j-aime/'))
            .at(-1);
        const pendingDesiredState = (pendingLike?.data as { is_liked?: unknown } | undefined)?.is_liked;
        const likesDelta = pendingLike && typeof pendingDesiredState === 'boolean'
            ? Number(pendingDesiredState) - Number(current.is_liked ?? false)
            : 0;
        setLiked(typeof pendingDesiredState === 'boolean' ? pendingDesiredState : current.is_liked ?? false);
        setLikesCount(Math.max(0, (current.likes_count ?? 0) + likesDelta));
        setSharesCount((current.shares_count ?? 0) + mutations.filter((mutation) =>
            mutation.url.endsWith('/partager/')).length);
    }, [announcement]);

    useEffect(() => {
        void refreshEngagement();
        return subscribeOutbox(() => { void refreshEngagement(); });
    }, [refreshEngagement]);

    const toggleLike = async () => {
        if (busy) return;
        setBusy('like');
        setMessage('');
        try {
            const nextLiked = !liked;
            const result = await sendOrQueue(
                {
                    method: 'post',
                    url: `/annonces/${announcement.id}/j-aime/`,
                    data: { is_liked: nextLiked },
                },
                () => ({ is_liked: nextLiked, likes_count: Math.max(0, likesCount + (nextLiked ? 1 : -1)) }),
            );
            setLiked(result.data.is_liked);
            setLikesCount(result.data.likes_count);
            if (result.queued) setMessage('Votre réaction sera synchronisée au retour du réseau.');
        } catch (error: any) {
            const detail = error?.response?.data?.detail;
            setMessage(typeof detail === 'string' ? detail : 'Impossible d’enregistrer votre mention J’aime.');
        } finally {
            setBusy(null);
        }
    };

    const sharePublication = async () => {
        if (busy) return;
        setBusy('share');
        setMessage('');
        const mediaUrl = announcement.media_url || announcement.video_url || announcement.image_url;
        const messageText = [
            announcement.title,
            announcement.body,
            mediaUrl,
        ].filter(Boolean).join('\n\n');

        try {
            const shareResult = await Share.share(
                { message: messageText, ...(mediaUrl ? { url: mediaUrl } : {}) },
                { dialogTitle: 'Partager la publication' },
            );
            if (shareResult.action !== Share.sharedAction) return;

            const queuedResult = await sendOrQueue(
                { method: 'post', url: `/annonces/${announcement.id}/partager/` },
                () => ({ shares_count: sharesCount + 1 }),
            );
            setSharesCount(queuedResult.data.shares_count);
            if (queuedResult.queued) setMessage('Le partage sera synchronisé au retour du réseau.');
        } catch (error: any) {
            const detail = error?.response?.data?.detail;
            setMessage(
                typeof detail === 'string'
                    ? detail
                    : 'La publication a été partagée, mais le compteur n’a pas pu être mis à jour.',
            );
        } finally {
            setBusy(null);
        }
    };

    return (
        <View>
            <View style={[styles.row, { borderTopColor: theme.accent, borderBottomColor: theme.accent }]}>
                <Pressable
                    accessibilityRole="button"
                    accessibilityLabel="Ouvrir les commentaires et commenter cette publication"
                    onPress={onCommentsPress}
                    disabled={!onCommentsPress}
                >
                    <Text style={[styles.count, { color: theme.primary }]}>
                        Commenter · {commentsCount ?? announcement.comments_count ?? 0}
                    </Text>
                </Pressable>
                <View style={styles.actions}>
                    <Pressable
                        accessibilityRole="button"
                        accessibilityLabel={liked ? 'Ne plus aimer cette publication' : 'Aimer cette publication'}
                        disabled={busy !== null}
                        onPress={toggleLike}
                    >
                        <Text style={[styles.actionText, { color: liked ? theme.primary : theme.text }]}>
                            {liked ? '♥ J’aime' : '♡ J’aime'} · {likesCount}
                        </Text>
                    </Pressable>
                    <Pressable
                        accessibilityRole="button"
                        accessibilityLabel="Partager la publication, par exemple sur WhatsApp"
                        disabled={busy !== null}
                        onPress={sharePublication}
                    >
                        <Text style={[styles.actionText, { color: theme.primary }]}>
                            {busy === 'share' ? 'Partage…' : '↗ Partager'} · {sharesCount}
                        </Text>
                    </Pressable>
                </View>
            </View>
            {message ? <Text style={[styles.message, { color: theme.text }]}>{message}</Text> : null}
        </View>
    );
}

const styles = StyleSheet.create({
    row: {
        minHeight: 46,
        marginTop: 12,
        paddingVertical: 10,
        borderTopWidth: 1,
        borderBottomWidth: 1,
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: 10,
    },
    count: {
        fontSize: 12,
        fontWeight: '600',
    },
    actions: {
        flexDirection: 'row',
        flexWrap: 'wrap',
        gap: 14,
    },
    actionText: {
        fontSize: 13,
        fontWeight: '700',
    },
    message: {
        marginTop: 7,
        fontSize: 12,
    },
});
