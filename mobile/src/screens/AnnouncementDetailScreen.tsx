import React, { useCallback, useState } from 'react';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import AnnouncementComments from '../components/AnnouncementComments';
import AnnouncementEngagement from '../components/AnnouncementEngagement';
import AnnouncementMedia from '../components/AnnouncementMedia';
import AnnouncementLinkPreview from '../components/AnnouncementLinkPreview';
import { RootStackParamList } from '../navigation/AppNavigator';
import { useTheme } from '../theme/LiturgicalTheme';
import useResponsiveLayout from '../hooks/useResponsiveLayout';

type Props = NativeStackScreenProps<RootStackParamList, 'AnnouncementDetail'>;

export default function AnnouncementDetailScreen({ route, navigation }: Props) {
    const theme = useTheme();
    const { formMaxWidth, horizontalPadding } = useResponsiveLayout();
    const { announcement } = route.params;
    const [commentsCount, setCommentsCount] = useState(announcement.comments_count ?? 0);
    const updateCommentCount = useCallback((_announcementId: string, count: number) => {
        setCommentsCount(count);
    }, []);

    return (
        <ScrollView style={{ backgroundColor: theme.background }} contentContainerStyle={[styles.container, { backgroundColor: theme.background, maxWidth: formMaxWidth, paddingHorizontal: horizontalPadding }]}>
            <View style={[styles.card, { backgroundColor: theme.card, borderColor: theme.accent }]}>
                <AnnouncementMedia
                    imageUrl={announcement.image_url}
                    videoUrl={announcement.video_url}
                    mediaUrl={announcement.media_url}
                    mediaType={announcement.media_type}
                />
                <AnnouncementLinkPreview url={announcement.link_url} title={announcement.link_title} />
                <View style={styles.metadata}>
                    <View style={[styles.tag, { backgroundColor: theme.primary }]}>
                        <Text style={styles.tagText}>{announcement.announcement_type?.toUpperCase() || 'INFO'}</Text>
                    </View>
                    {announcement.published_at ? (
                        <Text style={[styles.date, { color: theme.text }]}>{announcement.published_at}</Text>
                    ) : null}
                </View>
                <Text style={[styles.title, { color: theme.text }]}>{announcement.title}</Text>
                <Text selectable style={[styles.body, { color: theme.text }]}>{announcement.body}</Text>
                <AnnouncementEngagement announcement={announcement} commentsCount={commentsCount} />
                <AnnouncementComments
                    announcementId={announcement.id}
                    onCountChange={updateCommentCount}
                    onRequestLogin={() => navigation.navigate('Auth')}
                />
            </View>
        </ScrollView>
    );
}

const styles = StyleSheet.create({
    container: {
        flexGrow: 1,
        width: '100%',
        alignSelf: 'center',
        padding: 20,
    },
    card: {
        borderWidth: 1,
        borderRadius: 18,
        padding: 18,
        shadowColor: '#000',
        shadowOpacity: 0.05,
        shadowOffset: { width: 0, height: 8 },
        shadowRadius: 16,
        elevation: 4,
    },
    metadata: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 10,
        marginBottom: 14,
    },
    tag: {
        borderRadius: 999,
        paddingHorizontal: 12,
        paddingVertical: 6,
    },
    tagText: {
        color: '#fff',
        fontSize: 12,
        fontWeight: '700',
    },
    date: {
        flexShrink: 1,
        fontSize: 12,
        opacity: 0.75,
        textAlign: 'right',
    },
    title: {
        marginBottom: 14,
        fontSize: 22,
        fontWeight: '700',
        lineHeight: 29,
    },
    body: {
        fontSize: 16,
        lineHeight: 25,
    },
});
