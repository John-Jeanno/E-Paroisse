import React, { useCallback, useEffect, useState } from 'react';
import { FlatList, Pressable, StyleSheet, Text, View } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/AppNavigator';
import apiClient from '../api/apiClient';
import { getCachedJson, setCachedJson } from '../api/cacheService';
import AnnouncementMedia from '../components/AnnouncementMedia';
import AnnouncementLinkPreview from '../components/AnnouncementLinkPreview';
import AnnouncementComments from '../components/AnnouncementComments';
import AnnouncementEngagement from '../components/AnnouncementEngagement';
import type { Announcement } from '../types/Announcement';
import { useTheme } from '../theme/LiturgicalTheme';
import useResponsiveLayout from '../hooks/useResponsiveLayout';

type Props = NativeStackScreenProps<RootStackParamList, 'Annonces'>;

export default function AnnouncementsScreen({ navigation }: Props) {
    const theme = useTheme();
    const { isDesktop, contentMaxWidth, horizontalPadding } = useResponsiveLayout();
    const [announcements, setAnnouncements] = useState<Announcement[]>([]);
    const [commentCounts, setCommentCounts] = useState<Record<string, number>>({});
    const updateCommentCount = useCallback((announcementId: string, count: number) => {
        setCommentCounts((current) => ({ ...current, [announcementId]: count }));
    }, []);

    useEffect(() => {
        const loadAnnouncements = async () => {
            const cacheKey = 'announcements';
            const cached = await getCachedJson<Announcement[]>(cacheKey);
            if (cached) {
                setAnnouncements(cached);
            }

            try {
                const response = await apiClient.get('/annonces/');
                setAnnouncements(response.data);
                await setCachedJson(cacheKey, response.data);
            } catch {
                // Use cached data on failure.
            }
        };
        loadAnnouncements();
    }, []);

    return (
        <View style={[styles.container, { backgroundColor: theme.background, maxWidth: contentMaxWidth, paddingHorizontal: horizontalPadding }]}>
            <Text style={[styles.title, { color: theme.primary }]}>Annonces officielles</Text>
            <FlatList
                key={isDesktop ? 'desktop-announcements' : 'mobile-announcements'}
                data={announcements}
                numColumns={isDesktop ? 2 : 1}
                columnWrapperStyle={isDesktop ? styles.cardRow : undefined}
                keyExtractor={(item) => item.id}
                renderItem={({ item }) => (
                    <View style={[styles.card, isDesktop && styles.desktopCard, { backgroundColor: theme.card, borderColor: theme.accent }]}>
                        <AnnouncementMedia
                            imageUrl={item.image_url}
                            videoUrl={item.video_url}
                            mediaUrl={item.media_url}
                            mediaType={item.media_type}
                        />
                        <AnnouncementLinkPreview url={item.link_url} title={item.link_title} />
                        <View style={styles.cardHeader}>
                            <View style={[styles.tag, { backgroundColor: theme.primary }]}>
                                <Text style={styles.tagText}>{item.announcement_type?.toUpperCase() || 'INFO'}</Text>
                            </View>
                            {item.published_at ? <Text style={[styles.publishedAt, { color: theme.text }]}>{item.published_at}</Text> : null}
                        </View>
                        <Pressable
                            accessibilityRole="button"
                            accessibilityLabel={`Lire la publication : ${item.title}`}
                            onPress={() => navigation.navigate('AnnouncementDetail', { announcement: item })}
                        >
                            <Text style={[styles.cardTitle, { color: theme.text }]}>{item.title}</Text>
                            <Text style={[styles.cardBody, { color: theme.text }]} numberOfLines={3}>{item.body}</Text>
                            <Text style={[styles.readMore, { color: theme.primary }]}>Lire la publication complète →</Text>
                        </Pressable>
                        <AnnouncementEngagement
                            announcement={item}
                            commentsCount={commentCounts[item.id]}
                            onCommentsPress={() => navigation.navigate('AnnouncementDetail', { announcement: item })}
                        />
                        <AnnouncementComments
                            announcementId={item.id}
                            onCountChange={updateCommentCount}
                            onRequestLogin={() => navigation.navigate('Auth')}
                        />
                    </View>
                )}
                ListEmptyComponent={<Text style={[styles.emptyState, { color: theme.text }]}>Aucune annonce disponible.</Text>}
            />
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        width: '100%',
        alignSelf: 'center',
        padding: 24,
        backgroundColor: '#fff',
    },
    cardRow: {
        gap: 20,
        alignItems: 'flex-start',
    },
    desktopCard: {
        flex: 1,
        minWidth: 0,
    },
    title: {
        fontSize: 22,
        fontWeight: 'bold',
        marginBottom: 16,
    },
    card: {
        borderWidth: 1,
        borderColor: '#ddd',
        borderRadius: 18,
        padding: 18,
        marginBottom: 16,
        backgroundColor: '#fbfbfb',
        shadowColor: '#000',
        shadowOpacity: 0.05,
        shadowOffset: { width: 0, height: 8 },
        shadowRadius: 16,
        elevation: 6,
    },
    cardHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 12,
    },
    tag: {
        paddingVertical: 6,
        paddingHorizontal: 12,
        borderRadius: 999,
    },
    tagText: {
        color: '#fff',
        fontSize: 12,
        fontWeight: '700',
    },
    publishedAt: {
        fontSize: 12,
        opacity: 0.7,
    },
    cardTitle: {
        fontSize: 18,
        fontWeight: '700',
        marginBottom: 10,
    },
    cardBody: {
        fontSize: 14,
        color: '#555',
        lineHeight: 20,
    },
    readMore: {
        marginTop: 8,
        fontSize: 13,
        fontWeight: '700',
    },
    emptyState: {
        color: '#666',
        textAlign: 'center',
        marginTop: 24,
    },
});
