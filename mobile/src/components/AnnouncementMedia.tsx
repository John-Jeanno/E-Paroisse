import React from 'react';
import { Image, StyleSheet } from 'react-native';
import { useVideoPlayer, VideoView } from 'expo-video';

type Props = {
    imageUrl?: string;
    videoUrl?: string;
    mediaUrl?: string;
    mediaType?: 'image' | 'video' | '';
};

export default function AnnouncementMedia({ imageUrl, videoUrl, mediaUrl, mediaType }: Props) {
    const resolvedVideoUrl = mediaType ? (mediaType === 'video' ? mediaUrl : undefined) : videoUrl;
    const resolvedImageUrl = mediaType ? (mediaType === 'image' ? mediaUrl : undefined) : imageUrl;
    const player = useVideoPlayer(resolvedVideoUrl ?? null, (videoPlayer) => {
        videoPlayer.loop = false;
        videoPlayer.pause();
    });

    if (resolvedVideoUrl) {
        return (
            <VideoView
                player={player}
                style={styles.media}
                contentFit="cover"
                nativeControls
                fullscreenOptions={{ enable: true }}
            />
        );
    }

    if (resolvedImageUrl) {
        return <Image source={{ uri: resolvedImageUrl }} style={styles.media} resizeMode="cover" />;
    }

    return null;
}

const styles = StyleSheet.create({
    media: {
        width: '100%',
        aspectRatio: 1,
        borderRadius: 16,
        marginBottom: 14,
        overflow: 'hidden',
    },
});
