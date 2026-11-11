import React, { useState, useEffect } from 'react';
import { Button, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/AppNavigator';
import apiClient from '../api/apiClient';
import { useTheme } from '../theme/LiturgicalTheme';
import useResponsiveLayout from '../hooks/useResponsiveLayout';

type Props = NativeStackScreenProps<RootStackParamList, 'Onboarding'>;

type GroupItem = {
    id: string;
    name: string;
};

const defaultGroups: GroupItem[] = [
    { id: 'religieux', name: 'Religieux' },
    { id: 'frere', name: 'Frère' },
    { id: 'choriste', name: 'Choriste' },
    { id: 'charismatique', name: 'Charismatique' },
    { id: 'catechiste', name: 'Catéchiste' },
    { id: 'cv-av', name: 'CV-AV' },
    { id: 'scout-guide', name: 'Scout & Guide' },
    { id: 'jec', name: 'JEC' },
    { id: 'service-ordre', name: "Service d'Ordre" },
    { id: 'enfant-coeur', name: 'Enfant de Cœur' },
    { id: 'lecteur-messe', name: 'Lecteur de Messe' },
    { id: 'simple-fidele', name: 'Simple Fidèle' },
];

export default function OnboardingScreen({ navigation }: Props) {
    const theme = useTheme();
    const { formMaxWidth, horizontalPadding } = useResponsiveLayout();
    const [firstName, setFirstName] = useState('');
    const [lastName, setLastName] = useState('');
    const [group, setGroup] = useState('');
    const [groups, setGroups] = useState<GroupItem[]>(defaultGroups);
    const [dropdownVisible, setDropdownVisible] = useState(false);
    const [message, setMessage] = useState('');

    useEffect(() => {
        const loadGroups = async () => {
            try {
                const response = await apiClient.get('/groupes/');
                if (response.data?.length > 0) {
                    setGroups(response.data);
                }
            } catch {
                setGroups(defaultGroups);
            }
        };
        loadGroups();
    }, []);

    const handleSubmit = async () => {
        if (!firstName.trim() || !lastName.trim() || !group.trim()) {
            setMessage('Merci de remplir tous les champs.');
            return;
        }

        try {
            await apiClient.put('/auth/profile/', {
                first_name: firstName,
                last_name: lastName,
                group_name: group,
            });
            navigation.replace('Home');
        } catch {
            setMessage('Impossible d’enregistrer votre profil. Réessayez.');
        }
    };

    return (
        <ScrollView style={{ backgroundColor: theme.background }} contentContainerStyle={[styles.container, { backgroundColor: theme.background, maxWidth: formMaxWidth, paddingHorizontal: horizontalPadding }]}>
            <Text style={[styles.title, { color: theme.primary }]}>Personnalisez votre expérience</Text>
            <Text style={[styles.description, { color: theme.text }]}>Indiquez votre prénom, nom et votre entité paroissiale pour recevoir les annonces et contenus adaptés.</Text>
            <TextInput
                style={[styles.input, { borderColor: theme.primary, color: theme.text }]}
                placeholder="Prénom"
                placeholderTextColor="#999"
                value={firstName}
                onChangeText={setFirstName}
            />
            <TextInput
                style={[styles.input, { borderColor: theme.primary, color: theme.text }]}
                placeholder="Nom"
                placeholderTextColor="#999"
                value={lastName}
                onChangeText={setLastName}
            />
            <Pressable
                style={[styles.dropdown, { borderColor: theme.primary }]}
                onPress={() => setDropdownVisible((visible) => !visible)}
            >
                <Text style={[styles.dropdownText, { color: group ? theme.text : '#999' }]}>
                    {group || 'Entité paroissiale'}
                </Text>
            </Pressable>
            {dropdownVisible && (
                <View style={[styles.dropdownList, { borderColor: theme.primary, backgroundColor: theme.card }]}>
                    {groups.map((item) => (
                        <Pressable
                            key={item.id}
                            style={({ pressed }) => [
                                styles.dropdownItem,
                                { backgroundColor: pressed ? '#f0f0f0' : 'transparent' },
                            ]}
                            onPress={() => {
                                setGroup(item.name);
                                setDropdownVisible(false);
                            }}
                        >
                            <Text style={[styles.dropdownItemText, { color: theme.text }]}>{item.name}</Text>
                        </Pressable>
                    ))}
                </View>
            )}
            <Button title="Commencer" color={theme.primary} onPress={handleSubmit} />
            {message ? <Text style={[styles.message, { color: theme.text }]}>{message}</Text> : null}
        </ScrollView>
    );
}

const styles = StyleSheet.create({
    container: {
        flexGrow: 1,
        width: '100%',
        alignSelf: 'center',
        padding: 24,
        backgroundColor: '#fff',
    },
    title: {
        fontSize: 24,
        fontWeight: 'bold',
        marginBottom: 16,
    },
    description: {
        fontSize: 16,
        marginBottom: 24,
        color: '#333',
    },
    input: {
        borderWidth: 1,
        borderColor: '#ccc',
        borderRadius: 8,
        padding: 12,
        marginBottom: 16,
    },
    dropdown: {
        borderWidth: 1,
        borderRadius: 8,
        padding: 14,
        marginBottom: 16,
        justifyContent: 'center',
    },
    dropdownText: {
        fontSize: 16,
    },
    dropdownList: {
        borderWidth: 1,
        borderRadius: 8,
        marginBottom: 16,
        overflow: 'hidden',
    },
    dropdownItem: {
        paddingVertical: 12,
        paddingHorizontal: 14,
    },
    dropdownItemText: {
        fontSize: 16,
    },
    message: {
        marginTop: 16,
        color: '#d9534f',
    },
});
