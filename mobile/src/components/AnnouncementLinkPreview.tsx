import React from 'react';
import { Alert, Linking, Pressable, StyleSheet, Text, View } from 'react-native';
import { useTheme } from '../theme/LiturgicalTheme';

type Props = {
    url?: string;
    title?: string;
};

function getHost(url: string) {
    try {
        return new URL(url).hostname;
    } catch {
        return url;
    }
}

export default function AnnouncementLinkPreview({ url, title }: Props) {
    const theme = useTheme();
    if (!url) return null;

    return (
        <Pressable
            accessibilityRole="link"
            accessibilityLabel={`Ouvrir le lien : ${title || getHost(url)}`}
            onPress={() => {
                void Linking.openURL(url).catch(() => {
                    Alert.alert('Lien indisponible', 'Ce lien ne peut pas être ouvert sur cet appareil.');
                });
            }}
            style={[styles.card, { borderColor: theme.accent, backgroundColor: theme.background }]}
        >
            <View style={[styles.icon, { backgroundColor: theme.primary }]}>
                <Text style={styles.iconText}>↗</Text>
            </View>
            <View style={styles.copy}>
                <Text numberOfLines={2} style={[styles.title, { color: theme.text }]}>
                    {title || getHost(url)}
                </Text>
                <Text numberOfLines={1} style={[styles.host, { color: theme.primary }]}>
                    {getHost(url)}
                </Text>
            </View>
        </Pressable>
    );
}

const styles = StyleSheet.create({
    card: {
        flexDirection: 'row',
        alignItems: 'center',
        borderWidth: 1,
        borderRadius: 14,
        padding: 14,
        marginBottom: 14,
    },
    icon: {
        width: 42,
        height: 42,
        borderRadius: 12,
        alignItems: 'center',
        justifyContent: 'center',
        marginRight: 12,
    },
    iconText: {
        color: '#fff',
        fontSize: 22,
        fontWeight: '800',
    },
    copy: {
        flex: 1,
        minWidth: 0,
    },
    title: {
        fontSize: 15,
        fontWeight: '700',
        marginBottom: 4,
    },
    host: {
        fontSize: 12,
    },
});
