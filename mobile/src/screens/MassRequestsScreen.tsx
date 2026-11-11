import React, { useEffect, useState } from 'react';
import { FlatList, StyleSheet, Text, View } from 'react-native';
import { fetchMassRequests } from '../api/massRequestService';
import { useTheme } from '../theme/LiturgicalTheme';
import useResponsiveLayout from '../hooks/useResponsiveLayout';

type MassRequest = {
    id: number;
    message: string;
    preferred_date?: string;
    status: string;
};

export default function MassRequestsScreen() {
    const theme = useTheme();
    const { contentMaxWidth, horizontalPadding } = useResponsiveLayout();
    const [requests, setRequests] = useState<MassRequest[]>([]);

    useEffect(() => {
        fetchMassRequests().then(setRequests).catch(() => setRequests([]));
    }, []);

    return (
        <View style={[styles.container, { backgroundColor: theme.background, maxWidth: contentMaxWidth, paddingHorizontal: horizontalPadding }]}>
            <Text style={[styles.title, { color: theme.primary }]}>Mes demandes de messe</Text>
            <FlatList
                data={requests}
                keyExtractor={(item) => String(item.id)}
                renderItem={({ item }) => (
                    <View style={[styles.card, { backgroundColor: theme.card, borderColor: theme.accent }]}>
                        <Text style={[styles.date, { color: theme.primary }]}>{item.preferred_date || 'Date non précisée'}</Text>
                        <Text style={{ color: theme.text }}>{item.message}</Text>
                        <Text style={[styles.status, { color: theme.text }]}>Statut : {item.status}</Text>
                    </View>
                )}
                ListEmptyComponent={<Text style={{ color: theme.text }}>Aucune demande enregistrée.</Text>}
            />
        </View>
    );
}

const styles = StyleSheet.create({
    container: { flex: 1, width: '100%', alignSelf: 'center', padding: 24 },
    title: { fontSize: 22, fontWeight: 'bold', marginBottom: 16 },
    card: { borderWidth: 1, borderRadius: 8, padding: 16, marginBottom: 12 },
    date: { fontWeight: '700', marginBottom: 8 },
    status: { marginTop: 10, opacity: 0.7 },
});