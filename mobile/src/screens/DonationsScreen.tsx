import React, { useEffect, useState } from 'react';
import { ActivityIndicator, ScrollView, StyleSheet, Text, View } from 'react-native';
import { DonationSettings, fetchDonationSettings } from '../api/parishServices';
import { useTheme } from '../theme/LiturgicalTheme';
import useResponsiveLayout from '../hooks/useResponsiveLayout';

export default function DonationsScreen() {
    const theme = useTheme();
    const { contentMaxWidth, horizontalPadding } = useResponsiveLayout();
    const [settings, setSettings] = useState<DonationSettings | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        fetchDonationSettings()
            .then(setSettings)
            .catch(() => setError('Impossible de charger les informations de don. Réessayez plus tard.'))
            .finally(() => setLoading(false));
    }, []);

    return (
        <ScrollView
            style={{ backgroundColor: theme.background }}
            contentContainerStyle={[styles.container, {
                backgroundColor: theme.background,
                maxWidth: contentMaxWidth,
                paddingHorizontal: horizontalPadding,
            }]}
        >
            <Text style={[styles.intro, { color: theme.text }]}>
                Votre don contribue à soutenir les activités et la mission de la paroisse.
            </Text>
            {loading ? <ActivityIndicator color={theme.primary} style={styles.loader} /> : null}
            {error ? <Text style={styles.error}>{error}</Text> : null}
            {!loading && settings ? (
                <>
                    <View style={[styles.card, { backgroundColor: theme.card, borderColor: theme.accent }]}>
                        <Text style={[styles.heading, { color: theme.primary }]}>Wave</Text>
                        {settings.wave_identifier ? (
                            <>
                                <Text style={[styles.label, { color: theme.text }]}>Numéro ou identifiant de paiement</Text>
                                <Text selectable style={[styles.identifier, { color: theme.text }]}>
                                    {settings.wave_identifier}
                                </Text>
                            </>
                        ) : (
                            <Text style={[styles.unavailable, { color: theme.text }]}>
                                Le paiement Wave n’est pas encore configuré par le secrétariat.
                            </Text>
                        )}
                    </View>
                    <View style={[styles.card, { backgroundColor: theme.card, borderColor: theme.accent }]}>
                        <Text style={[styles.heading, { color: theme.primary }]}>Orange Money</Text>
                        {settings.orange_money_identifier ? (
                            <>
                                <Text style={[styles.label, { color: theme.text }]}>Numéro ou identifiant de paiement</Text>
                                <Text selectable style={[styles.identifier, { color: theme.text }]}>
                                    {settings.orange_money_identifier}
                                </Text>
                            </>
                        ) : (
                            <Text style={[styles.unavailable, { color: theme.text }]}>
                                Le paiement Orange Money n’est pas encore configuré par le secrétariat.
                            </Text>
                        )}
                    </View>
                    {settings.instructions ? (
                        <View style={[styles.card, { backgroundColor: theme.card, borderColor: theme.accent }]}>
                            <Text style={[styles.heading, { color: theme.primary }]}>Instructions</Text>
                            <Text style={[styles.instructions, { color: theme.text }]}>{settings.instructions}</Text>
                        </View>
                    ) : null}
                    {(settings.wave_identifier || settings.orange_money_identifier) ? (
                        <Text style={[styles.notice, { color: theme.text }]}>
                            Effectuez le transfert dans l’application de paiement correspondante. La confirmation du don
                            n’est pas automatisée dans cette version.
                        </Text>
                    ) : null}
                </>
            ) : null}
        </ScrollView>
    );
}

const styles = StyleSheet.create({
    container: { width: '100%', alignSelf: 'center', padding: 24 },
    intro: { fontSize: 15, lineHeight: 22, marginBottom: 18 },
    loader: { marginVertical: 24 },
    error: { color: '#b42318', marginBottom: 16 },
    card: { borderWidth: 1, borderRadius: 16, padding: 18, marginBottom: 14 },
    heading: { fontSize: 19, fontWeight: '700', marginBottom: 12 },
    label: { fontSize: 14, marginBottom: 6 },
    identifier: { fontSize: 18, fontWeight: '700' },
    unavailable: { fontSize: 14, lineHeight: 21 },
    instructions: { fontSize: 15, lineHeight: 22 },
    notice: { fontSize: 13, lineHeight: 19, opacity: 0.8, marginTop: 2 },
});
