import React, { useEffect, useState } from 'react';
import { Button, KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, TextInput, View, Pressable } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/AppNavigator';
import apiClient from '../api/apiClient';
import { fetchProfile } from '../api/profileService';
import { fetchGroups } from '../api/groupService';
import { getToken, setToken } from '../api/tokenStorage';
import { useTheme } from '../theme/LiturgicalTheme';
import useResponsiveLayout from '../hooks/useResponsiveLayout';
import Svg, { Path } from 'react-native-svg';

type Props = NativeStackScreenProps<RootStackParamList, 'Auth'>;

const defaultMembershipOptions = [
    'Religieux',
    'Frère',
    'Choriste',
    'Charismatique',
    'Catéchiste',
    'CV-AV',
    'Scout & Guide',
    'JEC',
    "Service d'Ordre",
    'Enfant de Cœur',
    'Lecteur de Messe',
    'Simple Fidèle',
];

export default function AuthScreen({ navigation }: Props) {
    const [mode, setMode] = useState<'login' | 'register' | 'forgot'>('login');
    const [firstName, setFirstName] = useState('');
    const [lastName, setLastName] = useState('');
    const [phone, setPhone] = useState('');
    const [selectedEntityNames, setSelectedEntityNames] = useState<string[]>([]);
    const [membershipOptions, setMembershipOptions] = useState(defaultMembershipOptions);
    const [membershipListVisible, setMembershipListVisible] = useState(false);
    const [password, setPassword] = useState('');
    const [otpCode, setOtpCode] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [resetRequested, setResetRequested] = useState(false);
    const [passwordVisible, setPasswordVisible] = useState(false);
    const [message, setMessage] = useState('');
    const { width, formMaxWidth, horizontalPadding } = useResponsiveLayout();

    const normalizePhone = (value: string) => value.replace(/[^+\d]/g, '');
    const formatPhoneForRequest = (value: string) => {
        const normalized = normalizePhone(value);
        if (!normalized.startsWith('+') && normalized.length > 0) {
            return `+${normalized}`;
        }
        return normalized;
    };

    useEffect(() => {
        const checkToken = async () => {
            try {
                const token = await getToken();
                if (!token) {
                    return;
                }

                const profile = await fetchProfile();
                const needsOnboarding = !profile.first_name || !profile.last_name || !profile.group_name;
                navigation.replace(needsOnboarding ? 'Onboarding' : 'Home');
            } catch { }
        };
        checkToken();
    }, [navigation]);

    useEffect(() => {
        let current = true;
        fetchGroups()
            .then((groups: { name: string }[]) => {
                if (current && groups.length > 0) {
                    setMembershipOptions(groups.map((group) => group.name));
                }
            })
            .catch(() => {
                if (current) {
                    setMessage('Impossible de charger toutes les entités paroissiales. Vérifiez votre connexion.');
                }
            });
        return () => {
            current = false;
        };
    }, []);

    const getErrorMessage = (error: any, fallback: string) => {
        const detail = error?.response?.data?.detail;
        if (typeof detail === 'string') {
            return detail;
        }
        const responseData = error?.response?.data;
        if (responseData && typeof responseData === 'object') {
            const validationMessage = Object.values(responseData)
                .flatMap((value) => Array.isArray(value) ? value : [value])
                .find((value) => typeof value === 'string');
            if (typeof validationMessage === 'string') {
                return validationMessage;
            }
        }
        return fallback;
    };

    const saveTokenAndOpenApp = async (token: string) => {
        await setToken(token);
        const profile = await fetchProfile();
        const needsOnboarding = !profile.first_name || !profile.last_name || !profile.group_name;
        navigation.replace(needsOnboarding ? 'Onboarding' : 'Home');
    };

    const handleSubmit = async () => {
        const normalizedPhone = normalizePhone(phone);
        if (!normalizedPhone || !password.trim()) {
            setMessage('Renseignez votre numéro de téléphone et votre mot de passe.');
            return;
        }

        if (mode === 'register' && (!firstName.trim() || !lastName.trim() || selectedEntityNames.length === 0)) {
            setMessage('Renseignez votre prénom, nom et sélectionnez au moins une entité paroissiale.');
            return;
        }

        try {
            const requestPhone = formatPhoneForRequest(normalizedPhone);
            const endpoint = mode === 'register' ? '/auth/register/' : '/auth/login/';
            const csrfResponse = await apiClient.get<{ csrfToken: string }>('/auth/csrf/');
            const payload = mode === 'register'
                ? {
                    first_name: firstName.trim(),
                    last_name: lastName.trim(),
                    phone_number: requestPhone,
                    parish_entity_names: selectedEntityNames,
                    group_name: selectedEntityNames[0],
                    password,
                }
                : { phone_number: requestPhone, password };
            const response = await apiClient.post(endpoint, payload, {
                headers: { 'X-CSRFToken': csrfResponse.data.csrfToken },
            });
            await saveTokenAndOpenApp(response.data.token);
        } catch (error) {
            setMessage(getErrorMessage(error, mode === 'register' ? 'Impossible de créer le compte.' : 'Numéro ou mot de passe incorrect.'));
        }
    };

    const handlePasswordResetRequest = async () => {
        const requestPhone = formatPhoneForRequest(phone);
        if (!requestPhone) {
            setMessage('Renseignez le numéro de téléphone utilisé lors de votre inscription.');
            return;
        }

        try {
            const response = await apiClient.post('/auth/password-reset/request/', {
                phone_number: requestPhone,
            });
            setResetRequested(true);
            if (response.data.otp_code) {
                setOtpCode(response.data.otp_code);
                setMessage(`Code de test (développement) : ${response.data.otp_code}`);
            } else {
                setMessage(response.data.detail);
            }
        } catch (error) {
            setMessage(getErrorMessage(error, 'Impossible de demander un code de récupération.'));
        }
    };

    const handlePasswordResetConfirm = async () => {
        const requestPhone = formatPhoneForRequest(phone);
        if (!otpCode.trim() || newPassword.length < 6) {
            setMessage('Saisissez le code reçu et un nouveau mot de passe de 6 caractères minimum.');
            return;
        }

        try {
            const response = await apiClient.post('/auth/password-reset/confirm/', {
                phone_number: requestPhone,
                otp_code: otpCode.trim(),
                new_password: newPassword,
            });
            setMode('login');
            setPassword('');
            setOtpCode('');
            setNewPassword('');
            setResetRequested(false);
            setMessage(response.data.detail);
        } catch (error) {
            setMessage(getErrorMessage(error, 'Impossible de modifier le mot de passe.'));
        }
    };

    const switchMode = (nextMode: 'login' | 'register') => {
        setMode(nextMode);
        setMessage('');
        setPassword('');
        setOtpCode('');
        setNewPassword('');
        setResetRequested(false);
        setPasswordVisible(false);
        setMembershipListVisible(false);
    };

    const theme = useTheme();

    return (
        <KeyboardAvoidingView style={[styles.container, { backgroundColor: theme.background, paddingHorizontal: horizontalPadding }]} behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
            <View style={[styles.form, { maxWidth: formMaxWidth, backgroundColor: width >= 900 ? theme.card : 'transparent' }, width >= 900 && styles.desktopCard]}>
                <Text style={[styles.subtitle, { color: theme.text }]}>
                    {mode === 'login' ? 'Connexion' : mode === 'register' ? 'Créer un compte' : 'Mot de passe oublié'}
                </Text>
                {mode !== 'forgot' ? (
                    <View style={[styles.modeRow, { borderColor: theme.accent }]}>
                        <Pressable onPress={() => switchMode('login')} style={[styles.modeButton, mode === 'login' && { backgroundColor: theme.primary }]}>
                            <Text style={[styles.modeButtonText, { color: mode === 'login' ? '#fff' : theme.primary }]}>Se connecter</Text>
                        </Pressable>
                        <Pressable onPress={() => switchMode('register')} style={[styles.modeButton, mode === 'register' && { backgroundColor: theme.primary }]}>
                            <Text style={[styles.modeButtonText, { color: mode === 'register' ? '#fff' : theme.primary }]}>Créer un compte</Text>
                        </Pressable>
                    </View>
                ) : (
                    <Text style={[styles.message, { color: theme.text }]}>
                        Saisissez votre numéro inscrit pour recevoir un code de vérification.
                    </Text>
                )}
                {mode === 'register' ? (
                    <>
                        <TextInput style={[styles.input, { borderColor: theme.primary, color: theme.text }]} placeholder="Prénom" placeholderTextColor="#999" value={firstName} onChangeText={setFirstName} />
                        <TextInput style={[styles.input, { borderColor: theme.primary, color: theme.text }]} placeholder="Nom" placeholderTextColor="#999" value={lastName} onChangeText={setLastName} />
                    </>
                ) : null}
                <TextInput
                    style={[styles.input, { borderColor: theme.primary, color: theme.text }]}
                    placeholder="N° Tel"
                    placeholderTextColor="#999"
                    keyboardType="phone-pad"
                    value={phone}
                    onChangeText={(value) => setPhone(normalizePhone(value))}
                    autoCapitalize="none"
                    autoCorrect={false}
                />
                {mode === 'register' ? (
                    <>
                        <Pressable
                            style={[styles.dropdown, { borderColor: theme.primary }]}
                            onPress={() => setMembershipListVisible((visible) => !visible)}
                        >
                            <Text style={[styles.dropdownText, { color: selectedEntityNames.length ? theme.text : '#999' }]}>
                                {selectedEntityNames.length
                                    ? selectedEntityNames.join(', ')
                                    : "Entités paroissiales (Sélectionnez votre ou vos entité(s) d'appartenance)"}
                            </Text>
                        </Pressable>
                        {membershipListVisible ? (
                            <View style={[styles.dropdownList, { borderColor: theme.primary, backgroundColor: theme.card }]}>
                                <ScrollView nestedScrollEnabled>
                                    {membershipOptions.map((membership) => (
                                        <Pressable
                                            key={membership}
                                            accessibilityRole="checkbox"
                                            accessibilityState={{ checked: selectedEntityNames.includes(membership) }}
                                            style={({ pressed }) => [
                                                styles.dropdownItem,
                                                { backgroundColor: pressed ? '#f0f0f0' : 'transparent' },
                                            ]}
                                            onPress={() => {
                                                setSelectedEntityNames((selected) => selected.includes(membership)
                                                    ? selected.filter((name) => name !== membership)
                                                    : [...selected, membership]);
                                            }}
                                        >
                                            <Text style={[styles.dropdownItemText, { color: theme.text }]}>
                                                {selectedEntityNames.includes(membership) ? '✓  ' : '□  '}{membership}
                                            </Text>
                                        </Pressable>
                                    ))}
                                </ScrollView>
                            </View>
                        ) : null}
                    </>
                ) : null}
                {mode !== 'forgot' ? <View style={[styles.passwordField, { borderColor: theme.primary }]}>
                    <TextInput
                        style={[styles.passwordInput, { color: theme.text }]}
                        placeholder="Mot de passe"
                        placeholderTextColor="#999"
                        secureTextEntry={!passwordVisible}
                        value={password}
                        onChangeText={setPassword}
                        autoCapitalize="none"
                        autoCorrect={false}
                    />
                    <Pressable
                        accessibilityRole="button"
                        accessibilityLabel={passwordVisible ? 'Masquer le mot de passe' : 'Afficher le mot de passe'}
                        accessibilityState={{ selected: passwordVisible }}
                        onPress={() => setPasswordVisible((visible) => !visible)}
                        hitSlop={8}
                        style={styles.passwordVisibilityButton}
                    >
                        <Svg width={22} height={22} viewBox="0 0 24 24" fill="none">
                            {passwordVisible ? (
                                <>
                                    <Path d="M3 3l18 18M10.6 10.7a2 2 0 0 0 2.7 2.7" stroke={theme.primary} strokeWidth={1.8} strokeLinecap="round" />
                                    <Path d="M9.9 5.2A10.7 10.7 0 0 1 12 5c6.4 0 10 7 10 7a15.3 15.3 0 0 1-3.2 4.1M6.2 6.3C3.5 8.1 2 12 2 12s3.6 7 10 7c1.1 0 2.1-.2 3-.5" stroke={theme.primary} strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" />
                                </>
                            ) : (
                                <>
                                    <Path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12Z" stroke={theme.primary} strokeWidth={1.8} />
                                    <Path d="M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6Z" stroke={theme.primary} strokeWidth={1.8} />
                                </>
                            )}
                        </Svg>
                        <Text style={[styles.passwordVisibilityText, { color: theme.primary }]}>
                            {passwordVisible ? 'Masquer' : 'Afficher'}
                        </Text>
                    </Pressable>
                </View> : null}
                {mode === 'forgot' && resetRequested ? (
                    <>
                        <TextInput
                            style={[styles.input, { borderColor: theme.primary, color: theme.text }]}
                            placeholder="Code de vérification à 6 chiffres"
                            placeholderTextColor="#999"
                            keyboardType="number-pad"
                            value={otpCode}
                            onChangeText={setOtpCode}
                            maxLength={6}
                        />
                        <TextInput
                            style={[styles.input, { borderColor: theme.primary, color: theme.text }]}
                            placeholder="Nouveau mot de passe (6 caractères minimum)"
                            placeholderTextColor="#999"
                            secureTextEntry
                            value={newPassword}
                            onChangeText={setNewPassword}
                            autoCapitalize="none"
                            autoCorrect={false}
                        />
                    </>
                ) : null}
                {mode === 'login' ? (
                    <>
                        <Button title="Se connecter" color={theme.primary} onPress={handleSubmit} />
                        <Pressable onPress={() => {
                            setMode('forgot');
                            setMessage('');
                            setResetRequested(false);
                        }}>
                            <Text style={[styles.forgotPassword, { color: theme.primary }]}>Mot de passe oublié ?</Text>
                        </Pressable>
                    </>
                ) : mode === 'register' ? (
                    <Button title="Créer mon compte" color={theme.primary} onPress={handleSubmit} />
                ) : resetRequested ? (
                    <Button title="Définir mon nouveau mot de passe" color={theme.primary} onPress={handlePasswordResetConfirm} />
                ) : (
                    <Button title="Recevoir un code de vérification" color={theme.primary} onPress={handlePasswordResetRequest} />
                )}
                {mode === 'forgot' ? (
                    <Pressable onPress={() => switchMode('login')}>
                        <Text style={[styles.forgotPassword, { color: theme.primary }]}>Retour à la connexion</Text>
                    </Pressable>
                ) : null}
                {message ? <Text style={[styles.message, { color: theme.text }]}>{message}</Text> : null}
            </View>
        </KeyboardAvoidingView>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        width: '100%',
        alignSelf: 'center',
        justifyContent: 'center',
        backgroundColor: '#fff',
    },
    form: {
        width: '100%',
        alignSelf: 'center',
        paddingVertical: 36,
    },
    desktopCard: {
        marginVertical: 48,
        padding: 40,
        borderRadius: 20,
        shadowColor: '#132c22',
        shadowOpacity: 0.1,
        shadowOffset: { width: 0, height: 12 },
        shadowRadius: 28,
        elevation: 5,
    },
    subtitle: {
        fontSize: 16,
        marginBottom: 24,
        textAlign: 'center',
    },
    modeRow: {
        flexDirection: 'row',
        marginBottom: 20,
        borderWidth: 1,
        borderColor: '#ddd',
        borderRadius: 8,
        overflow: 'hidden',
    },
    modeButton: {
        flex: 1,
        paddingVertical: 11,
        alignItems: 'center',
    },
    modeButtonText: {
        fontWeight: '600',
        fontSize: 13,
    },
    input: {
        borderWidth: 1,
        borderColor: '#ccc',
        borderRadius: 8,
        padding: 12,
        marginBottom: 16,
    },
    passwordField: {
        minHeight: 48,
        flexDirection: 'row',
        alignItems: 'center',
        borderWidth: 1,
        borderRadius: 8,
        marginBottom: 16,
    },
    passwordInput: {
        flex: 1,
        padding: 12,
    },
    passwordVisibilityButton: {
        minWidth: 82,
        minHeight: 48,
        flexDirection: 'row',
        gap: 5,
        alignItems: 'center',
        justifyContent: 'center',
        paddingHorizontal: 8,
    },
    passwordVisibilityText: { fontSize: 12, fontWeight: '700' },
    forgotPassword: {
        marginTop: 16,
        textAlign: 'center',
        fontWeight: '600',
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
        maxHeight: 240,
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
        color: '#555',
        textAlign: 'center',
    },
});
