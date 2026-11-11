import React, { useEffect, useRef, useState } from 'react';
import { Platform, Pressable, Text } from 'react-native';
import { setAudioModeAsync, useAudioPlayer, useAudioPlayerStatus } from 'expo-audio';
import apiClient from '../api/apiClient';
import { getToken } from '../api/tokenStorage';
import { useTheme } from '../theme/LiturgicalTheme';

type Props = {
    audioPath: string;
};

export default function VoiceMessagePlayer({ audioPath }: Props) {
    const theme = useTheme();
    const player = useAudioPlayer(null, { updateInterval: 250 });
    const status = useAudioPlayerStatus(player);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const objectUrl = useRef<string | null>(null);
    const shouldPlay = useRef(false);
    const isLocalAudio = /^(blob:|file:|data:)/i.test(audioPath);
    const audioUrl = apiClient.getUri({ url: audioPath });

    useEffect(() => {
        if (!status.isLoaded || !shouldPlay.current) return;
        shouldPlay.current = false;
        player.play();
    }, [player, status.isLoaded]);

    useEffect(() => {
        if (!status.error) return;
        setLoading(false);
        setError('Lecture audio impossible.');
    }, [status.error]);

    useEffect(() => () => {
        player.pause();
        if (objectUrl.current) URL.revokeObjectURL(objectUrl.current);
    }, [player]);

    const togglePlayback = async () => {
        setError('');
        if (status.playing) {
            player.pause();
            return;
        }
        try {
            await setAudioModeAsync({ allowsRecording: false, playsInSilentMode: true });
        } catch {
            setError('Impossible d’activer la lecture audio.');
            return;
        }
        if (status.isLoaded) {
            await player.seekTo(0);
            player.play();
            return;
        }
        setLoading(true);
        try {
            if (isLocalAudio) {
                player.replace({ uri: audioPath });
            } else {
                const token = await getToken();
                if (!token) throw new Error('Session expirée.');
                if (Platform.OS === 'web') {
                    const response = await fetch(audioUrl, { headers: { Authorization: `Token ${token}` } });
                    if (!response.ok) throw new Error('Audio indisponible.');
                    objectUrl.current = URL.createObjectURL(await response.blob());
                    player.replace({ uri: objectUrl.current });
                } else {
                    player.replace({ uri: audioUrl, headers: { Authorization: `Token ${token}` } });
                }
            }
            shouldPlay.current = true;
        } catch {
            setError('Impossible de charger ce message vocal.');
        } finally {
            setLoading(false);
        }
    };

    const timeLabel = status.duration > 0
        ? `${Math.floor(status.currentTime)} / ${Math.ceil(status.duration)} s`
        : 'Message vocal';

    return (
        <>
            <Pressable
                accessibilityRole="button"
                accessibilityLabel={status.playing ? 'Mettre en pause le message vocal' : 'Lire le message vocal'}
                onPress={() => void togglePlayback()}
                style={{ paddingVertical: 8, paddingHorizontal: 10, borderRadius: 8, backgroundColor: theme.accent, alignSelf: 'flex-start' }}
            >
                <Text style={{ color: theme.text, fontWeight: '700' }}>
                    {loading ? 'Chargement…' : status.playing ? '⏸ Pause' : '▶ Écouter'} · {timeLabel}
                </Text>
            </Pressable>
            {error ? <Text style={{ color: '#b42318', marginTop: 4 }}>{error}</Text> : null}
        </>
    );
}
