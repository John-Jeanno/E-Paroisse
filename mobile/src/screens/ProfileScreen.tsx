import React, { useEffect, useState } from 'react';
import { Button, FlatList, StyleSheet, Text, TextInput, TouchableOpacity, View } from 'react-native';
import OfflineNotice from '../components/OfflineNotice';
import { fetchGroups } from '../api/groupService';
import { fetchProfile, updateProfile } from '../api/profileService';
import { clearToken } from '../api/tokenStorage';
import { RootStackParamList } from '../navigation/AppNavigator';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useTheme } from '../theme/LiturgicalTheme';
import useResponsiveLayout from '../hooks/useResponsiveLayout';

type GroupItem = {
    id: string;
    name: string;
};

type Props = NativeStackScreenProps<RootStackParamList, 'Profil'>;

export default function ProfileScreen({ navigation }: Props) {
    const theme = useTheme();
    const { formMaxWidth, horizontalPadding } = useResponsiveLayout();
    const [firstName, setFirstName] = useState('');
    const [lastName, setLastName] = useState('');
    const [selectedEntityNames, setSelectedEntityNames] = useState<string[]>([]);
    const [groups, setGroups] = useState<GroupItem[]>([]);
    const [message, setMessage] = useState('');

    useEffect(() => {
        const loadProfile = async () => {
            try {
                const profile = await fetchProfile();
                setFirstName(profile.first_name || '');
                setLastName(profile.last_name || '');
                setSelectedEntityNames(
                    profile.parish_entity_names?.length
                        ? profile.parish_entity_names
                        : profile.group_name ? [profile.group_name] : [],
                );
            } catch {
                setMessage('Impossible de charger le profil.');
            }
        };

        const loadGroups = async () => {
            try {
                const groupData = await fetchGroups();
                setGroups(groupData);
            } catch {
                // ignore group load failure, keep custom entry
            }
        };

        loadProfile();
        loadGroups();
    }, []);

    const handleSave = async () => {
        if (selectedEntityNames.length === 0) {
            setMessage('Sélectionnez au moins une entité paroissiale.');
            return;
        }
        try {
            await updateProfile({
                first_name: firstName,
                last_name: lastName,
                parish_entity_names: selectedEntityNames,
            });
            setMessage('Profil mis à jour.');
        } catch {
            setMessage('Erreur lors de la mise à jour du profil.');
        }
    };

    const toggleEntity = (name: string) => {
        setSelectedEntityNames((selected) => selected.includes(name)
            ? selected.filter((item) => item !== name)
            : [...selected, name]);
    };

    const handleLogout = async () => {
        await clearToken();
        navigation.reset({ index: 0, routes: [{ name: 'Auth' }] });
    };

    return (
        <View style={[styles.container, { backgroundColor: theme.background, maxWidth: formMaxWidth, paddingHorizontal: horizontalPadding }]}>
            <OfflineNotice />
            <Text style={[styles.title, { color: theme.primary }]}>Mon profil</Text>
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
            {groups.length > 0 ? (
                <View style={styles.groupContainer}>
                    <Text style={[styles.groupLabel, { color: theme.text }]}>Entités paroissiales</Text>
                    <FlatList
                        data={groups}
                        horizontal
                        keyExtractor={(item) => item.id}
                        renderItem={({ item }) => (
                            <TouchableOpacity
                                accessibilityRole="checkbox"
                                accessibilityState={{ checked: selectedEntityNames.includes(item.name) }}
                                style={[
                                    styles.groupChip,
                                    { borderColor: theme.accent, backgroundColor: theme.card },
                                    selectedEntityNames.includes(item.name) && { backgroundColor: theme.primary, borderColor: theme.primary },
                                ]}
                                onPress={() => toggleEntity(item.name)}
                            >
                                <Text style={[
                                    styles.groupChipText,
                                    { color: theme.primary },
                                    selectedEntityNames.includes(item.name) && styles.groupChipTextSelected,
                                ]}>
                                    {selectedEntityNames.includes(item.name) ? '✓ ' : ''}{item.name}
                                </Text>
                            </TouchableOpacity>
                        )}
                        showsHorizontalScrollIndicator={false}
                    />
                </View>
            ) : null}
            <Button title="Enregistrer" color={theme.primary} onPress={handleSave} />
            <View style={styles.logoutButton}>
                <Button title="Déconnexion" color="#b42318" onPress={handleLogout} />
            </View>
            {message ? <Text style={[styles.message, { color: theme.text }]}>{message}</Text> : null}
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
    input: {
        borderWidth: 1,
        borderColor: '#ccc',
        borderRadius: 8,
        padding: 12,
        marginBottom: 16,
    },
    message: {
        marginTop: 16,
        color: '#333',
    },
    logoutButton: {
        marginTop: 16,
    },
    groupContainer: {
        marginBottom: 16,
    },
    groupLabel: {
        fontSize: 14,
        marginBottom: 8,
        color: '#555',
    },
    groupChip: {
        paddingVertical: 8,
        paddingHorizontal: 14,
        borderRadius: 20,
        borderWidth: 1,
        borderColor: '#b9d8e8',
        marginRight: 10,
        backgroundColor: '#fff',
    },
    groupChipSelected: {
        backgroundColor: '#6b4e3d',
    },
    groupChipText: {
        color: '#6b4e3d',
    },
    groupChipTextSelected: {
        color: '#fff',
    },
});
