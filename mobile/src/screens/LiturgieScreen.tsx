import React, { useEffect, useState } from 'react';
import { Button, FlatList, Platform, Pressable, StyleSheet, Text, View } from 'react-native';
import DateTimePicker, { DateTimePickerEvent } from '@react-native-community/datetimepicker';
import apiClient from '../api/apiClient';
import { getCachedJson, setCachedJson } from '../api/cacheService';
import { useTheme } from '../theme/LiturgicalTheme';
import useResponsiveLayout from '../hooks/useResponsiveLayout';

type LiturgicalReading = {
    id: string;
    date: string;
    title: string;
    content: string;
    source?: string;
};

export default function LiturgieScreen() {
    const theme = useTheme();
    const { contentMaxWidth, horizontalPadding } = useResponsiveLayout();
    const [lectures, setLectures] = useState<LiturgicalReading[]>([]);
    const [selectedDate, setSelectedDate] = useState(new Date());
    const [pendingDate, setPendingDate] = useState(new Date());
    const [pickerVisible, setPickerVisible] = useState(false);

    useEffect(() => {
        const loadLectures = async () => {
            const dateKey = selectedDate.toISOString().slice(0, 10);
            const cacheKey = `liturgie-${dateKey}`;
            const cached = await getCachedJson<LiturgicalReading[]>(cacheKey);
            if (cached) {
                setLectures(cached);
            }

            try {
                const response = await apiClient.get('/lectures/', { params: { date: dateKey } });
                setLectures(response.data);
                await setCachedJson(cacheKey, response.data);
            } catch {
                // Use cached data on failure.
            }
        };
        loadLectures();
    }, [selectedDate]);

    const handleDateChange = (event: DateTimePickerEvent, date?: Date) => {
        if (Platform.OS !== 'ios') {
            setPickerVisible(false);
        }
        if (event.type !== 'dismissed' && date) {
            setPendingDate(date);
        }
    };

    const dateLabel = selectedDate.toLocaleDateString('fr-FR', {
        day: 'numeric',
        month: 'long',
        year: 'numeric',
    });

    return (
        <View style={[styles.container, { backgroundColor: theme.background, maxWidth: contentMaxWidth, paddingHorizontal: horizontalPadding }]}>
            <Text style={[styles.title, { color: theme.primary }]}>Ressources liturgiques</Text>
            <View style={[styles.datePanel, { backgroundColor: theme.card, borderColor: theme.primary }]}>
                <Text style={[styles.label, { color: theme.text }]}>Consulter une date précise</Text>
                {Platform.OS === 'web' ? (
                    React.createElement('input', {
                        'aria-label': 'Choisir la date des lectures',
                        type: 'date',
                        value: pendingDate.toISOString().slice(0, 10),
                        style: styles.dateInput,
                        onChange: (event: { target: { value: string } }) => {
                            const date = new Date(`${event.target.value}T12:00:00`);
                            if (!Number.isNaN(date.getTime())) {
                                setPendingDate(date);
                            }
                        },
                    })
                ) : (
                    <>
                        <Pressable style={[styles.dateButton, { borderColor: theme.primary }]} onPress={() => setPickerVisible(true)}>
                            <Text style={{ color: theme.text }}>{pendingDate.toLocaleDateString('fr-FR')}</Text>
                        </Pressable>
                        {pickerVisible ? <DateTimePicker value={pendingDate} mode="date" onChange={handleDateChange} /> : null}
                    </>
                )}
                <Button title="Afficher les lectures" color={theme.primary} onPress={() => setSelectedDate(pendingDate)} />
                <Text style={[styles.selectedDate, { color: theme.text }]}>Date affichée : {dateLabel}</Text>
            </View>
            <FlatList
                data={lectures}
                keyExtractor={(item) => item.id}
                renderItem={({ item }) => (
                    <View style={[styles.card, { backgroundColor: theme.card, borderColor: theme.accent }]}>
                        <Text style={[styles.cardTitle, { color: theme.text }]}>{item.title}</Text>
                        <Text style={[styles.cardBody, { color: theme.text }]}>{item.content}</Text>
                    </View>
                )}
                ListEmptyComponent={<Text style={[styles.emptyState, { color: theme.text }]}>Aucune lecture disponible.</Text>}
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
    title: {
        fontSize: 22,
        fontWeight: 'bold',
        marginBottom: 16,
    },
    label: {
        fontWeight: '600',
        marginBottom: 6,
    },
    datePanel: {
        borderWidth: 1,
        borderRadius: 10,
        padding: 14,
        marginBottom: 16,
    },
    dateInput: {
        boxSizing: 'border-box',
        fontFamily: 'inherit',
        fontSize: 16,
        marginBottom: 16,
        padding: 12,
        width: '100%',
    } as never,
    selectedDate: {
        fontSize: 13,
        marginTop: 10,
    },
    dateButton: {
        borderWidth: 1,
        borderRadius: 8,
        padding: 14,
        marginBottom: 16,
    },
    card: {
        borderWidth: 1,
        borderColor: '#ddd',
        borderRadius: 10,
        padding: 16,
        marginBottom: 12,
    },
    cardTitle: {
        fontSize: 18,
        fontWeight: '600',
        marginBottom: 8,
    },
    cardBody: {
        fontSize: 14,
        color: '#555',
    },
    emptyState: {
        color: '#666',
        textAlign: 'center',
        marginTop: 24,
    },
});
