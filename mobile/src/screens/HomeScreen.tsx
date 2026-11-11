import React, { useCallback, useEffect, useRef, useState } from 'react';
import { ActivityIndicator, NativeScrollEvent, NativeSyntheticEvent, Pressable, ScrollView, StyleSheet, Text, TextInput, TouchableOpacity, View } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/AppNavigator';
import apiClient from '../api/apiClient';
import AnnouncementMedia from '../components/AnnouncementMedia';
import AnnouncementLinkPreview from '../components/AnnouncementLinkPreview';
import AnnouncementComments from '../components/AnnouncementComments';
import AnnouncementEngagement from '../components/AnnouncementEngagement';
import type { Announcement } from '../types/Announcement';
import { useTheme } from '../theme/LiturgicalTheme';
import useResponsiveLayout from '../hooks/useResponsiveLayout';

type Props = NativeStackScreenProps<RootStackParamList, 'Home'>;

type LiturgicalReadingItem = {
    id: string;
    title: string;
    content: string;
};

type Profile = {
    first_name: string;
    group_name: string;
};

export default function HomeScreen({ navigation }: Props) {
    const theme = useTheme();
    const responsive = useResponsiveLayout();
    const { isDesktop, contentMaxWidth, horizontalPadding } = responsive;
    const [profile, setProfile] = useState<Profile | null>(null);
    const [announcements, setAnnouncements] = useState<Announcement[]>([]);
    const [feedHasMore, setFeedHasMore] = useState(true);
    const [feedLoading, setFeedLoading] = useState(false);
    const [feedLoadingMore, setFeedLoadingMore] = useState(false);
    const [feedError, setFeedError] = useState('');
    const [commentCounts, setCommentCounts] = useState<Record<string, number>>({});
    const [reading, setReading] = useState<LiturgicalReadingItem | null>(null);
    const [searchQuery, setSearchQuery] = useState('');
    const feedPage = useRef(0);
    const feedLoadingRef = useRef(false);
    const updateCommentCount = useCallback((announcementId: string, count: number) => {
        setCommentCounts((current) => ({ ...current, [announcementId]: count }));
    }, []);

    const loadAnnouncementPage = useCallback(async (page: number, replace = false) => {
        if (feedLoadingRef.current) return;
        feedLoadingRef.current = true;
        setFeedError('');
        if (replace) setFeedLoading(true);
        else setFeedLoadingMore(true);

        try {
            const response = await apiClient.get('/annonces/fil/', { params: { page } });
            const results = response.data.results as Announcement[];
            setAnnouncements((current) => {
                if (replace) return results;
                const existingIds = new Set(current.map((item) => item.id));
                return [...current, ...results.filter((item) => !existingIds.has(item.id))];
            });
            feedPage.current = page;
            setFeedHasMore(Boolean(response.data.next));
        } catch {
            setFeedError('Impossible de charger les publications. Faites défiler pour réessayer.');
        } finally {
            feedLoadingRef.current = false;
            setFeedLoading(false);
            setFeedLoadingMore(false);
        }
    }, []);

    useEffect(() => {
        const loadHome = async () => {
            try {
                const profileResponse = await apiClient.get('/auth/profile/');
                setProfile(profileResponse.data);
            } catch {
                setProfile(null);
            }

            await loadAnnouncementPage(1, true);

            try {
                const lectureResponse = await apiClient.get('/lectures/');
                const lectureData = lectureResponse.data?.[0];
                if (lectureData) {
                    setReading(lectureData);
                }
            } catch {
                setReading(null);
            }
        };
        void loadHome();
    }, [loadAnnouncementPage]);

    const handleFeedScroll = (event: NativeSyntheticEvent<NativeScrollEvent>) => {
        const { contentOffset, contentSize, layoutMeasurement } = event.nativeEvent;
        const isNearBottom = layoutMeasurement.height + contentOffset.y >= contentSize.height - 600;
        if (isNearBottom && feedHasMore && !feedLoadingRef.current) {
            void loadAnnouncementPage(feedPage.current + 1);
        }
    };

    const greeting = profile?.first_name
        ? `Bonjour ${profile.first_name}`
        : 'Bienvenue sur Paroisse NDA';

    const description = profile?.group_name
        ? `Contenu personnalisé pour ${profile.group_name}`
        : 'Personnalisez votre profil pour des annonces adaptées.';

    const movementChips = ['Chorale', 'Scouts', 'JEC', 'CV-AV'];

    return (
        <ScrollView
            style={{ backgroundColor: theme.background }}
            contentContainerStyle={[styles.container, { backgroundColor: theme.background, maxWidth: contentMaxWidth, paddingHorizontal: horizontalPadding }]}
            onScroll={handleFeedScroll}
            scrollEventThrottle={400}
        >
            <Text style={[styles.welcome, { color: theme.primary }]}>{greeting}</Text>
            <Text style={[styles.description, { color: theme.text }]}>{description}</Text>
            <View style={styles.searchRow}>
                <View style={styles.searchInputContainer}>
                    <TextInput
                        accessibilityLabel="Rechercher dans l’application"
                        placeholder="Rechercher une personne, un thème…"
                        placeholderTextColor="#888"
                        returnKeyType="search"
                        value={searchQuery}
                        onChangeText={setSearchQuery}
                        onSubmitEditing={() => navigation.navigate('Search', { query: searchQuery.trim() })}
                        style={[styles.searchInput, { borderColor: theme.accent, color: theme.text, backgroundColor: theme.card }]}
                    />
                    {searchQuery.length > 0 ? (
                        <Pressable
                            accessibilityRole="button"
                            accessibilityLabel="Effacer la recherche"
                            onPress={() => setSearchQuery('')}
                            style={styles.clearSearchButton}
                        >
                            <Text style={[styles.clearSearchButtonText, { color: theme.text }]}>×</Text>
                        </Pressable>
                    ) : null}
                </View>
                <TouchableOpacity
                    accessibilityRole="button"
                    accessibilityLabel="Lancer la recherche"
                    onPress={() => navigation.navigate('Search', { query: searchQuery.trim() })}
                    style={[styles.searchButton, { backgroundColor: theme.primary }]}
                >
                    <Text style={styles.searchButtonText}>🔍</Text>
                </TouchableOpacity>
            </View>

            <View style={[styles.dashboardLayout, isDesktop && styles.dashboardDesktop]}>
                <View style={[styles.dashboardSideColumn, isDesktop && styles.dashboardDesktopColumn]}>
                    <View style={styles.section}>
                    <Text style={[styles.sectionTitle, { color: theme.primary }]}>Mon espace</Text>
                    <View style={styles.buttonRowLarge}>
                        <TouchableOpacity style={[styles.iconCard, { backgroundColor: theme.card, borderColor: theme.accent }]} onPress={() => navigation.navigate('Profil')}>
                            <Text style={[styles.iconCardTitle, { color: theme.text }]}>Profil</Text>
                        </TouchableOpacity>
                        <TouchableOpacity style={[styles.iconCard, { backgroundColor: theme.card, borderColor: theme.accent }]} onPress={() => navigation.navigate('MassRequests')}>
                            <Text style={[styles.iconCardTitle, { color: theme.text }]}>Mes demandes</Text>
                        </TouchableOpacity>
                        <TouchableOpacity style={[styles.iconCard, { backgroundColor: theme.card, borderColor: theme.accent }]} onPress={() => navigation.navigate('RequestMass')}>
                            <Text style={[styles.iconCardTitle, { color: theme.text }]}>Demander une messe</Text>
                        </TouchableOpacity>
                        <TouchableOpacity style={[styles.iconCard, { backgroundColor: theme.card, borderColor: theme.accent }]} onPress={() => navigation.navigate('Catechese')}>
                            <Text style={[styles.iconCardTitle, { color: theme.text }]}>📖 Catéchèse</Text>
                        </TouchableOpacity>
                        <TouchableOpacity style={[styles.iconCard, { backgroundColor: theme.card, borderColor: theme.accent }]} onPress={() => navigation.navigate('SpiritualGame')}>
                            <Text style={[styles.iconCardTitle, { color: theme.text }]}>🎮 Jeux spirituels</Text>
                        </TouchableOpacity>
                        <TouchableOpacity style={[styles.iconCard, { backgroundColor: theme.card, borderColor: theme.accent }]} onPress={() => navigation.navigate('MassSchedule')}>
                            <Text style={[styles.iconCardTitle, { color: theme.text }]}>Heures de messes</Text>
                        </TouchableOpacity>
                        <TouchableOpacity style={[styles.iconCard, { backgroundColor: theme.card, borderColor: theme.accent }]} onPress={() => navigation.navigate('Donations')}>
                            <Text style={[styles.iconCardTitle, { color: theme.text }]}>Dons · Wave · Orange Money</Text>
                        </TouchableOpacity>
                    </View>
                    <TouchableOpacity style={[styles.messagingButton, { backgroundColor: theme.primary }]} onPress={() => navigation.navigate('Messaging')}>
                        <Text style={styles.messagingButtonText}>Messagerie</Text>
                        <Text style={styles.messagingButtonHint}>Échanger en privé avec un paroissien</Text>
                    </TouchableOpacity>
                    </View>

                    <View style={[styles.section, styles.liturgySection]}>
                        <View style={[styles.liturgyHeader, { backgroundColor: theme.primary }]}>
                            <Text style={styles.liturgyHeaderDate}>Liturgie du jour</Text>
                            <Text style={styles.liturgyHeaderLabel}>{theme.seasonLabel}</Text>
                        </View>
                        {reading ? (
                            <View style={[styles.card, { backgroundColor: theme.card, borderColor: theme.accent }]}>
                                <Text style={[styles.cardTitle, { color: theme.text }]}>{reading.title}</Text>
                                <Text style={[styles.cardBody, { color: theme.text }]} numberOfLines={3}>{reading.content}</Text>
                            </View>
                        ) : (
                            <Text style={styles.empty}>Aucune lecture disponible.</Text>
                        )}
                        <View style={styles.buttonRowSmall}>
                            <TouchableOpacity style={[styles.secondaryButton, { borderColor: theme.primary }]} onPress={() => navigation.navigate('Liturgie')}>
                                <Text style={[styles.secondaryButtonText, { color: theme.primary }]}>Voir la liturgie</Text>
                            </TouchableOpacity>
                            <TouchableOpacity style={[styles.secondaryButton, { borderColor: theme.primary }]} onPress={() => navigation.navigate('LiturgicalCalendar')}>
                                <Text style={[styles.secondaryButtonText, { color: theme.primary }]}>Calendrier</Text>
                            </TouchableOpacity>
                        </View>
                    </View>
                </View>

                <View style={[styles.section, isDesktop && styles.dashboardMainColumn]}>
                    <Text style={[styles.sectionTitle, { color: theme.primary }]}>Fil d’actualité</Text>
                    {announcements.length > 0 ? (
                        announcements.map((item) => (
                            <View key={item.id} style={[styles.card, { backgroundColor: theme.card, borderColor: theme.accent }]}>
                                <AnnouncementMedia
                                    imageUrl={item.image_url}
                                    videoUrl={item.video_url}
                                    mediaUrl={item.media_url}
                                    mediaType={item.media_type}
                                />
                                <AnnouncementLinkPreview url={item.link_url} title={item.link_title} />
                                <Pressable
                                    accessibilityRole="button"
                                    accessibilityLabel={`Lire la publication : ${item.title}`}
                                    onPress={() => navigation.navigate('AnnouncementDetail', { announcement: item })}
                                >
                                    <Text style={[styles.cardTitle, { color: theme.text }]}>{item.title}</Text>
                                    <Text style={[styles.cardBody, { color: theme.text }]} numberOfLines={2}>{item.body}</Text>
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
                        ))
                    ) : feedLoading ? (
                        <ActivityIndicator color={theme.primary} />
                    ) : (
                        <Text style={styles.empty}>Aucune publication disponible.</Text>
                    )}
                    {feedError ? (
                        <TouchableOpacity
                            accessibilityRole="button"
                            onPress={() => void loadAnnouncementPage(feedPage.current + 1, feedPage.current === 0)}
                        >
                            <Text style={styles.feedError}>{feedError} Réessayer</Text>
                        </TouchableOpacity>
                    ) : null}
                    {feedLoadingMore ? <ActivityIndicator color={theme.primary} style={styles.feedLoading} /> : null}
                </View>
            </View>
        </ScrollView>
    );
}

const styles = StyleSheet.create({
    container: {
        flexGrow: 1,
        width: '100%',
        alignSelf: 'center',
        padding: 24,
        backgroundColor: '#fff',
    },
    dashboardLayout: {
        width: '100%',
    },
    dashboardDesktop: {
        flexDirection: 'row-reverse',
        alignItems: 'flex-start',
        gap: 28,
    },
    dashboardMainColumn: {
        flex: 1.8,
        minWidth: 0,
    },
    dashboardSideColumn: {
        marginBottom: 24,
    },
    dashboardDesktopColumn: {
        flex: 1,
        minWidth: 300,
        maxWidth: 380,
    },
    banner: {
        borderRadius: 16,
        padding: 16,
        marginBottom: 20,
    },
    bannerTitle: {
        fontSize: 18,
        fontWeight: '700',
        marginBottom: 6,
    },
    bannerText: {
        fontSize: 14,
        lineHeight: 20,
    },
    welcome: {
        fontSize: 26,
        fontWeight: 'bold',
        marginBottom: 8,
    },
    description: {
        fontSize: 16,
        marginBottom: 24,
        color: '#555',
    },
    searchRow: {
        flexDirection: 'row',
        gap: 10,
        marginBottom: 24,
    },
    searchInputContainer: {
        flex: 1,
        minWidth: 0,
        justifyContent: 'center',
    },
    searchInput: {
        borderWidth: 1,
        borderRadius: 14,
        paddingLeft: 15,
        paddingRight: 44,
        paddingVertical: 12,
        fontSize: 15,
    },
    clearSearchButton: {
        position: 'absolute',
        right: 6,
        width: 36,
        height: 36,
        alignItems: 'center',
        justifyContent: 'center',
    },
    clearSearchButtonText: {
        fontSize: 24,
        lineHeight: 28,
    },
    searchButton: {
        width: 52,
        alignItems: 'center',
        justifyContent: 'center',
        borderRadius: 14,
    },
    searchButtonText: {
        color: '#fff',
        fontSize: 19,
    },
    section: {
        marginBottom: 24,
    },
    sectionTitle: {
        fontSize: 18,
        fontWeight: '700',
        marginBottom: 12,
    },
    liturgySection: {
        padding: 0,
    },
    liturgyHeader: {
        padding: 16,
        borderRadius: 14,
        marginBottom: 12,
    },
    liturgyHeaderDate: {
        fontSize: 16,
        color: '#fff',
        fontWeight: '700',
        marginBottom: 6,
    },
    liturgyHeaderLabel: {
        color: '#fff',
        fontSize: 14,
    },
    card: {
        borderWidth: 1,
        borderColor: '#ddd',
        borderRadius: 18,
        padding: 18,
        marginBottom: 14,
        backgroundColor: '#fbfbfb',
        shadowColor: '#000',
        shadowOpacity: 0.04,
        shadowOffset: { width: 0, height: 4 },
        shadowRadius: 8,
        elevation: 4,
    },
    cardTitle: {
        fontSize: 16,
        fontWeight: '700',
        marginBottom: 8,
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
    empty: {
        fontSize: 14,
        color: '#666',
        marginBottom: 12,
    },
    feedError: {
        color: '#b42318',
        fontSize: 14,
        marginBottom: 12,
    },
    feedLoading: {
        marginVertical: 12,
    },
    primaryButton: {
        borderRadius: 14,
        paddingVertical: 14,
        alignItems: 'center',
        marginTop: 8,
    },
    primaryButtonText: {
        color: '#fff',
        fontWeight: '700',
        fontSize: 16,
    },
    secondaryButton: {
        flex: 1,
        borderWidth: 1,
        borderRadius: 12,
        paddingVertical: 12,
        alignItems: 'center',
        marginRight: 10,
    },
    secondaryButtonText: {
        fontWeight: '700',
        fontSize: 14,
    },
    buttonRowSmall: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        marginTop: 12,
    },
    buttonRowLarge: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
    },
    iconCard: {
        flex: 1,
        minWidth: 100,
        borderRadius: 18,
        borderWidth: 1,
        padding: 18,
        justifyContent: 'center',
        alignItems: 'center',
        marginRight: 10,
        marginBottom: 12,
    },
    iconCardTitle: {
        fontSize: 14,
        fontWeight: '700',
    },
    messagingButton: {
        borderRadius: 12,
        padding: 16,
        marginTop: 4,
        alignItems: 'center',
    },
    messagingButtonText: {
        color: '#fff',
        fontSize: 16,
        fontWeight: '700',
    },
    messagingButtonHint: {
        color: '#fff',
        fontSize: 13,
        marginTop: 4,
        opacity: 0.9,
    },
    buttonWrapper: {
        flex: 1,
        marginRight: 10,
    },
    calendarButton: {
        marginTop: 12,
    },
});
