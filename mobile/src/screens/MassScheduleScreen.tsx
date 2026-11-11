import React, { useEffect, useState } from 'react';
import { ActivityIndicator, ScrollView, StyleSheet, Text, View } from 'react-native';
import { fetchMassSchedules, MassSchedule } from '../api/parishServices';
import { useTheme } from '../theme/LiturgicalTheme';
import useResponsiveLayout from '../hooks/useResponsiveLayout';

const WEEKDAYS = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche'];

export default function MassScheduleScreen() {
    const theme = useTheme();
    const { contentMaxWidth, horizontalPadding } = useResponsiveLayout();
    const [schedules, setSchedules] = useState<MassSchedule[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        fetchMassSchedules()
            .then(setSchedules)
            .catch(() => setError('Impossible de charger les horaires de messe. Réessayez plus tard.'))
            .finally(() => setLoading(false));
    }, []);

    const recurring = schedules.filter((item) => item.date === null);
    const special = schedules.filter((item) => item.date !== null);
    const sortByTime = (left: MassSchedule, right: MassSchedule) => left.time.localeCompare(right.time);

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
                Retrouvez ici les horaires communiqués par le secrétariat paroissial.
            </Text>
            {loading ? <ActivityIndicator color={theme.primary} style={styles.loader} /> : null}
            {error ? <Text style={styles.error}>{error}</Text> : null}
            {!loading && !error && schedules.length === 0 ? (
                <Text style={[styles.empty, { color: theme.text }]}>
                    Aucun horaire n’a encore été publié par le secrétariat.
                </Text>
            ) : null}
            {WEEKDAYS.map((day, weekday) => {
                const daySchedules = recurring.filter((item) => item.weekday === weekday).sort(sortByTime);
                if (!daySchedules.length) return null;
                return (
                    <View key={day} style={[styles.card, { backgroundColor: theme.card, borderColor: theme.accent }]}>
                        <Text style={[styles.day, { color: theme.primary }]}>{day}</Text>
                        {daySchedules.map((item) => (
                            <View key={item.id} style={styles.row}>
                                <Text style={[styles.time, { color: theme.text }]}>{item.time.slice(0, 5)}</Text>
                                <Text style={[styles.location, { color: theme.text }]}>{item.location}</Text>
                            </View>
                        ))}
                    </View>
                );
            })}
            {special.length > 0 ? (
                <>
                    <Text style={[styles.heading, { color: theme.primary }]}>Dates particulières</Text>
                    {special.sort((left, right) =>
                        `${left.date} ${left.time}`.localeCompare(`${right.date} ${right.time}`)).map((item) => (
                        <View key={item.id} style={[styles.card, { backgroundColor: theme.card, borderColor: theme.accent }]}>
                            <Text style={[styles.day, { color: theme.primary }]}>
                                {new Date(`${item.date}T12:00:00`).toLocaleDateString('fr-FR', {
                                    weekday: 'long',
                                    day: 'numeric',
                                    month: 'long',
                                    year: 'numeric',
                                })}
                            </Text>
                            <View style={styles.row}>
                                <Text style={[styles.time, { color: theme.text }]}>{item.time.slice(0, 5)}</Text>
                                <Text style={[styles.location, { color: theme.text }]}>{item.location}</Text>
                            </View>
                        </View>
                    ))}
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
    empty: { fontSize: 15, paddingVertical: 16 },
    heading: { fontSize: 19, fontWeight: '700', marginTop: 16, marginBottom: 10 },
    card: { borderWidth: 1, borderRadius: 16, padding: 16, marginBottom: 12 },
    day: { fontSize: 17, fontWeight: '700', marginBottom: 10, textTransform: 'capitalize' },
    row: { flexDirection: 'row', alignItems: 'center', paddingVertical: 5 },
    time: { width: 64, fontWeight: '700', fontSize: 16 },
    location: { flex: 1, fontSize: 15 },
});
