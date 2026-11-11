import React from 'react';
import { Pressable, StyleSheet, Text } from 'react-native';
import { useTheme } from '../theme/LiturgicalTheme';
import { useOfflineStatus } from './OfflineProvider';
import { retryFailedMutations } from '../api/offlineService';

export default function OfflineNotice() {
    const theme = useTheme();
    const { isOnline, pendingCount, failedCount, pendingActions, synchronize } = useOfflineStatus();
    if (isOnline && pendingCount === 0) return null;

    return (
        <Pressable
            accessibilityRole={isOnline ? 'button' : undefined}
            onPress={() => {
                if (isOnline) {
                    void retryFailedMutations().then(synchronize).catch((error: unknown) => {
                        console.error('Les actions en attente ne peuvent pas être relancées.', error);
                    });
                }
            }}
            style={[styles.container, { backgroundColor: theme.accent }]}
        >
            <Text style={[styles.text, { color: theme.text }]}>
                {isOnline
                    ? `${pendingCount} action(s) en attente de synchronisation${failedCount ? `, dont ${failedCount} en échec` : ''}. Touchez pour réessayer.`
                    : `Hors ligne. Les contenus déjà synchronisés restent disponibles${pendingCount ? ` · ${pendingCount} action(s) seront envoyées au retour du réseau` : ''}${failedCount ? ` · ${failedCount} action(s) nécessitent une nouvelle tentative` : ''}.`}
            </Text>
            {pendingActions.slice(0, 5).map((action) => (
                <Text key={action.id} style={[styles.actionText, { color: theme.text }]}>
                    · {action.label}{action.status === 'failed' ? ' — échec, appuyez pour réessayer' : ' — en attente'}
                </Text>
            ))}
        </Pressable>
    );
}

const styles = StyleSheet.create({
    container: {
        padding: 12,
        borderRadius: 8,
        marginBottom: 20,
    },
    text: {
        fontWeight: '600',
    },
    actionText: {
        marginTop: 4,
        fontSize: 12,
    },
});
