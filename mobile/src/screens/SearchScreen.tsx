import React, { useEffect, useMemo, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/AppNavigator';
import { searchParishContent, GlobalSearchResult } from '../api/searchService';
import { lessons } from './CatecheseScreen';
import { useTheme } from '../theme/LiturgicalTheme';
import useResponsiveLayout from '../hooks/useResponsiveLayout';

type Props = NativeStackScreenProps<RootStackParamList, 'Search'>;
type LessonResult = { kind: 'lesson'; id: string; title: string; subtitle: string };
type Result = GlobalSearchResult | LessonResult;

const kindLabels: Record<Result['kind'], string> = {
    announcement: 'Publication',
    reading: 'Liturgie',
    question: 'Question biblique',
    parishioner: 'Paroissien',
    lesson: 'Catéchèse',
};

export default function SearchScreen({ route, navigation }: Props) {
    const theme = useTheme();
    const { contentMaxWidth, horizontalPadding } = useResponsiveLayout();
    const [query, setQuery] = useState(route.params?.query ?? '');
    const [remoteResults, setRemoteResults] = useState<GlobalSearchResult[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    useEffect(() => {
        setQuery(route.params?.query ?? '');
    }, [route.params?.query]);

    useEffect(() => {
        const normalizedQuery = query.trim();
        if (normalizedQuery.length < 2) {
            setRemoteResults([]);
            setError('');
            setLoading(false);
            return;
        }

        let current = true;
        const timeout = setTimeout(() => {
            setLoading(true);
            searchParishContent(normalizedQuery)
                .then((results) => {
                    if (current) {
                        setRemoteResults(results);
                        setError('');
                    }
                })
                .catch(() => {
                    if (current) {
                        setRemoteResults([]);
                        setError('La recherche en ligne est momentanément indisponible.');
                    }
                })
                .finally(() => {
                    if (current) setLoading(false);
                });
        }, 250);
        return () => {
            current = false;
            clearTimeout(timeout);
        };
    }, [query]);

    const results = useMemo<Result[]>(() => {
        const normalizedQuery = query.trim().toLocaleLowerCase('fr');
        if (normalizedQuery.length < 2) return [];
        const localLessons = lessons
            .filter((lesson) => [
                lesson.title,
                lesson.age,
                lesson.reference,
                lesson.objective,
                lesson.keyPhrase,
                lesson.story,
                lesson.activity,
                lesson.prayer,
                ...lesson.steps,
            ].some((value) => value.toLocaleLowerCase('fr').includes(normalizedQuery)))
            .slice(0, 8)
            .map((lesson) => ({
                kind: 'lesson' as const,
                id: lesson.id,
                title: lesson.title,
                subtitle: lesson.reference,
            }));
        return [...remoteResults, ...localLessons];
    }, [query, remoteResults]);

    const openResult = (result: Result) => {
        if (result.kind === 'announcement' && result.announcement) {
            navigation.navigate('AnnouncementDetail', { announcement: result.announcement });
        } else if (result.kind === 'reading') {
            navigation.navigate('Liturgie');
        } else if (result.kind === 'question') {
            navigation.navigate('SpiritualGame');
        } else if (result.kind === 'parishioner' && result.profile_id) {
            navigation.navigate('Messaging', { contactId: result.profile_id });
        } else if (result.kind === 'lesson') {
            navigation.navigate('Catechese', { lessonId: result.id });
        }
    };

    return (
        <ScrollView
            style={{ backgroundColor: theme.background }}
            contentContainerStyle={[
                styles.container,
                { backgroundColor: theme.background, maxWidth: contentMaxWidth, paddingHorizontal: horizontalPadding },
            ]}
            keyboardShouldPersistTaps="handled"
        >
            <Text style={[styles.description, { color: theme.text }]}>
                Recherchez dans les publications visibles, la liturgie, la catéchèse, les questions bibliques et l’annuaire paroissial.
            </Text>
            <View style={styles.inputContainer}>
                <TextInput
                    autoFocus
                    accessibilityLabel="Rechercher dans l’application"
                    placeholder="Un mot, une personne, un thème…"
                    placeholderTextColor="#888"
                    returnKeyType="search"
                    value={query}
                    onChangeText={setQuery}
                    style={[styles.input, { borderColor: theme.primary, color: theme.text, backgroundColor: theme.card }]}
                />
                {query.length > 0 ? (
                    <Pressable
                        accessibilityRole="button"
                        accessibilityLabel="Effacer la recherche"
                        onPress={() => setQuery('')}
                        style={styles.clearButton}
                    >
                        <Text style={[styles.clearButtonText, { color: theme.text }]}>×</Text>
                    </Pressable>
                ) : null}
            </View>
            {loading ? <ActivityIndicator color={theme.primary} style={styles.loading} /> : null}
            {error ? <Text style={styles.error}>{error}</Text> : null}
            {query.trim().length < 2 ? (
                <Text style={[styles.hint, { color: theme.text }]}>Saisissez au moins deux caractères pour lancer la recherche.</Text>
            ) : results.length > 0 ? (
                <View style={styles.results}>
                    {results.map((result) => (
                        <Pressable
                            key={`${result.kind}:${result.id}`}
                            accessibilityRole="button"
                            onPress={() => openResult(result)}
                            style={[styles.result, { backgroundColor: theme.card, borderColor: theme.accent }]}
                        >
                            <Text style={[styles.kind, { color: theme.primary }]}>{kindLabels[result.kind]}</Text>
                            <Text style={[styles.title, { color: theme.text }]}>{result.title}</Text>
                            <Text style={[styles.subtitle, { color: theme.text }]}>{result.subtitle}</Text>
                        </Pressable>
                    ))}
                </View>
            ) : !loading && !error ? (
                <Text style={[styles.hint, { color: theme.text }]}>Aucun résultat pour cette recherche.</Text>
            ) : null}
        </ScrollView>
    );
}

const styles = StyleSheet.create({
    container: { flexGrow: 1, width: '100%', alignSelf: 'center', padding: 24 },
    description: { fontSize: 15, lineHeight: 22, marginBottom: 14 },
    inputContainer: { justifyContent: 'center' },
    input: { borderWidth: 1, borderRadius: 14, paddingLeft: 16, paddingRight: 48, paddingVertical: 13, fontSize: 16 },
    clearButton: { position: 'absolute', right: 6, width: 38, height: 38, alignItems: 'center', justifyContent: 'center' },
    clearButtonText: { fontSize: 26, lineHeight: 30 },
    loading: { marginTop: 16 },
    error: { color: '#b42318', marginTop: 14 },
    hint: { marginTop: 18, fontSize: 14 },
    results: { marginTop: 16 },
    result: { borderWidth: 1, borderRadius: 14, padding: 16, marginBottom: 10 },
    kind: { fontSize: 12, fontWeight: '700', marginBottom: 5, textTransform: 'uppercase' },
    title: { fontSize: 16, fontWeight: '700', marginBottom: 5 },
    subtitle: { fontSize: 13, opacity: 0.75 },
});
