import React from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { useTheme } from '../theme/LiturgicalTheme';
import useResponsiveLayout from '../hooks/useResponsiveLayout';

export default function LiturgicalCalendarScreen() {
    const theme = useTheme();
    const { contentMaxWidth, horizontalPadding } = useResponsiveLayout();

    return (
        <ScrollView style={{ backgroundColor: theme.background }} contentContainerStyle={[styles.container, { backgroundColor: theme.background, maxWidth: contentMaxWidth, paddingHorizontal: horizontalPadding }]}>
            <View style={[styles.header, { backgroundColor: theme.primary }]}>
                <Text style={[styles.headerTitle, { color: theme.primary === '#FFFFFF' ? '#111' : '#fff' }]}>Calendrier liturgique</Text>
                <Text style={[styles.headerSubtitle, { color: theme.primary === '#FFFFFF' ? '#111' : '#fff' }]}>
                    Saison actuelle : {theme.seasonLabel}
                </Text>
            </View>
            <View style={[styles.card, { backgroundColor: theme.card, borderColor: theme.accent }]}>
                <Text style={[styles.cardTitle, { color: theme.primary }]}>{theme.seasonLabel}</Text>
                <Text style={[styles.cardBody, { color: theme.text }]}>{theme.seasonDescription}</Text>
            </View>
            <View style={[styles.card, { backgroundColor: theme.card, borderColor: theme.accent }]}>
                <Text style={[styles.cardTitle, { color: theme.primary }]}>Couleurs des temps liturgiques</Text>
                <View style={styles.bulletRow}>
                    <Text style={[styles.bulletPoint, { color: theme.text }]}>• Avent / Carême : violet</Text>
                </View>
                <View style={styles.bulletRow}>
                    <Text style={[styles.bulletPoint, { color: theme.text }]}>• Gaudete / Laetare : rose</Text>
                </View>
                <View style={styles.bulletRow}>
                    <Text style={[styles.bulletPoint, { color: theme.text }]}>• Noël / Pâques : blanc/or</Text>
                </View>
                <View style={styles.bulletRow}>
                    <Text style={[styles.bulletPoint, { color: theme.text }]}>• Pentecôte : rouge</Text>
                </View>
                <View style={styles.bulletRow}>
                    <Text style={[styles.bulletPoint, { color: theme.text }]}>• Temps ordinaire : vert</Text>
                </View>
            </View>
            <View style={[styles.card, { backgroundColor: theme.card, borderColor: theme.accent }]}>
                <Text style={[styles.cardTitle, { color: theme.primary }]}>Pratique</Text>
                <Text style={[styles.cardBody, { color: theme.text }]}>La saison liturgique indique le temps célébré par l’Église. Les couleurs de l’application s’y adaptent automatiquement : violet pour l’Avent et le Carême, rose pour Gaudete et Laetare, blanc et or pour Noël et Pâques, rouge pour la Semaine Sainte et la Pentecôte, vert pour le temps ordinaire.</Text>
            </View>
        </ScrollView>
    );
}

const styles = StyleSheet.create({
    container: {
        flexGrow: 1,
        width: '100%',
        alignSelf: 'center',
        padding: 24,
    },
    header: {
        borderRadius: 16,
        padding: 20,
        marginBottom: 20,
    },
    headerTitle: {
        fontSize: 24,
        fontWeight: 'bold',
        marginBottom: 8,
    },
    headerSubtitle: {
        fontSize: 16,
        opacity: 0.9,
    },
    card: {
        borderWidth: 1,
        borderRadius: 14,
        padding: 18,
        marginBottom: 16,
    },
    cardTitle: {
        fontSize: 18,
        fontWeight: '700',
        marginBottom: 10,
    },
    cardBody: {
        fontSize: 15,
        lineHeight: 22,
    },
    bulletRow: {
        marginBottom: 8,
    },
    bulletPoint: {
        fontSize: 14,
        lineHeight: 20,
    },
});
