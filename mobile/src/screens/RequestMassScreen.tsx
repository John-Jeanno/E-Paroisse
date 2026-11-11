import React, { useEffect, useState } from 'react';
import { Button, Platform, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import DateTimePicker, { DateTimePickerEvent } from '@react-native-community/datetimepicker';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/AppNavigator';
import { createMassRequest, fetchMassRequestPaymentInfo } from '../api/massRequestService';
import { getToken } from '../api/tokenStorage';
import { readOfflineDraft, writeOfflineDraft } from '../api/offlineStorage';
import { useTheme } from '../theme/LiturgicalTheme';
import useResponsiveLayout from '../hooks/useResponsiveLayout';

type Props = NativeStackScreenProps<RootStackParamList, 'RequestMass'>;

export default function RequestMassScreen({ navigation }: Props) {
    const theme = useTheme();
    const { formMaxWidth, horizontalPadding } = useResponsiveLayout();
    const [phone, setPhone] = useState('');
    const [email, setEmail] = useState('');
    const [locality, setLocality] = useState('');
    const [preferredDate, setPreferredDate] = useState<Date | null>(null);
    const [pickerVisible, setPickerVisible] = useState(false);
    const [message, setMessage] = useState('');
    const [status, setStatus] = useState('');
    const [paymentPhone, setPaymentPhone] = useState<string | null>(null);
    const [contactPhone, setContactPhone] = useState('77 123 45 67');
    const [paymentInfoError, setPaymentInfoError] = useState(false);
    const [draftReady, setDraftReady] = useState(false);

    useEffect(() => {
        let active = true;
        void getToken()
            .then((token) => readOfflineDraft<{
                phone: string;
                email: string;
                locality: string;
                preferredDate: string | null;
                message: string;
            }>(token, 'mass-request-form'))
            .then((draft) => {
                if (!active) return;
                if (draft) {
                    setPhone(draft.phone);
                    setEmail(draft.email);
                    setLocality(draft.locality ?? '');
                    const restoredDate = draft.preferredDate ? new Date(draft.preferredDate) : null;
                    setPreferredDate(
                        restoredDate && !Number.isNaN(restoredDate.getTime())
                            ? restoredDate
                            : null,
                    );
                    setMessage(draft.message);
                }
            })
            .catch((error: unknown) => {
                console.error('Le brouillon de demande de messe n’a pas pu être restauré.', error);
            })
            .finally(() => {
                if (active) setDraftReady(true);
            });
        return () => { active = false; };
    }, []);

    useEffect(() => {
        if (!draftReady) return undefined;
        const timeout = setTimeout(() => {
            void getToken()
                .then((token) => writeOfflineDraft(token, 'mass-request-form', {
                    phone,
                    email,
                    locality,
                    preferredDate: preferredDate?.toISOString() ?? null,
                    message,
                }))
                .catch((error: unknown) => {
                    console.error('Le brouillon de demande de messe n’a pas pu être enregistré.', error);
                });
        }, 250);
        return () => clearTimeout(timeout);
    }, [draftReady, email, locality, message, phone, preferredDate]);

    useEffect(() => {
        let active = true;

        fetchMassRequestPaymentInfo()
            .then((paymentInfo) => {
                if (active) {
                    setPaymentPhone(paymentInfo.payment_phone.trim());
                    setContactPhone(paymentInfo.contact_phone.trim() || '77 123 45 67');
                }
            })
            .catch(() => {
                if (active) {
                    setPaymentInfoError(true);
                }
            });

        return () => {
            active = false;
        };
    }, []);

    const handleSubmit = async () => {
        if (!phone.trim()) {
            setStatus('Veuillez saisir votre numéro de téléphone.');
            return;
        }
        if (!locality.trim()) {
            setStatus('Veuillez indiquer votre ville et votre quartier de résidence.');
            return;
        }
        if (!message.trim()) {
            setStatus('Veuillez saisir vos intentions de messe.');
            return;
        }

        try {
            const result = await createMassRequest({
                phone: phone.trim(),
                contact_email: email,
                locality: locality.trim(),
                preferred_date: preferredDate?.toISOString(),
                message,
            });
            if (result.data.blocked) {
                setStatus(result.data.detail ?? 'Veuillez contacter la paroisse pour faire votre demande.');
                return;
            }
            setStatus(result.queued
                ? 'Demande enregistrée sur cet appareil. Elle sera envoyée au retour du réseau.'
                : 'Demande envoyée. Merci.');
            setPhone('');
            setEmail('');
            setLocality('');
            setPreferredDate(null);
            setMessage('');
        } catch (err) {
            setStatus('Échec de l’envoi. Réessayez.');
        }
    };

    const handleDateChange = (event: DateTimePickerEvent, date?: Date) => {
        if (Platform.OS !== 'ios') {
            setPickerVisible(false);
        }
        if (event.type !== 'dismissed' && date) {
            setPreferredDate(date);
        }
    };

    const formatDate = (date: Date) => date.toLocaleString('fr-FR', {
        dateStyle: 'long',
        timeStyle: 'short',
    });

    return (
        <View style={[styles.container, { backgroundColor: theme.background, maxWidth: formMaxWidth, paddingHorizontal: horizontalPadding }]}>
            <Text style={[styles.title, { color: theme.primary }]}>Demander une messe</Text>
            <Text style={[styles.helper, { color: theme.text }]}>Précisez la date souhaitée (si connue) et vos intentions de messe.</Text>
            <View style={[styles.paymentNotice, { backgroundColor: theme.card, borderColor: theme.accent }]}>
                <Text style={[styles.paymentInstruction, { color: theme.text }]}>Pour une demande de messe à Ouakam, contactez la paroisse au :</Text>
                <Text selectable style={[styles.paymentPhone, { color: theme.primary }]}>{contactPhone}</Text>
            </View>
            <View style={[styles.paymentNotice, { backgroundColor: theme.card, borderColor: theme.accent }]}>
                <Text style={[styles.paymentInstruction, { color: theme.text }]}>Envoyer sur ce numéro le montant :</Text>
                {paymentInfoError ? (
                    <Text style={[styles.paymentStatus, { color: theme.text }]}>Impossible de charger le numéro de paiement. Réessayez plus tard.</Text>
                ) : paymentPhone === null ? (
                    <Text style={[styles.paymentStatus, { color: theme.text }]}>Chargement du numéro de paiement…</Text>
                ) : paymentPhone ? (
                    <Text selectable style={[styles.paymentPhone, { color: theme.primary }]}>{paymentPhone}</Text>
                ) : (
                    <Text selectable style={[styles.paymentPhone, { color: theme.primary }]}>77 123 45 67</Text>
                )}
            </View>
            <TextInput style={[styles.input, { borderColor: theme.primary, color: theme.text }]} placeholder="Téléphone (obligatoire)" placeholderTextColor="#999" value={phone} onChangeText={setPhone} keyboardType="phone-pad" accessibilityLabel="Téléphone obligatoire" />
            <TextInput style={[styles.input, { borderColor: theme.primary, color: theme.text }]} placeholder="Email (optionnel)" placeholderTextColor="#999" value={email} onChangeText={setEmail} keyboardType="email-address" />
            <TextInput
                style={[styles.input, { borderColor: theme.primary, color: theme.text }]}
                placeholder="Domicilié(e) à (ville, quartier) ?"
                placeholderTextColor="#999"
                value={locality}
                onChangeText={setLocality}
                accessibilityLabel="Ville et quartier de résidence, obligatoire"
            />
            <Text style={[styles.fieldLabel, { color: theme.text }]}>Date et heure préférées</Text>
            {Platform.OS === 'web' ? (
                React.createElement('input', {
                    type: 'datetime-local',
                    style: {
                        border: `1px solid ${theme.primary}`,
                        borderRadius: 8,
                        boxSizing: 'border-box',
                        color: theme.text,
                        fontFamily: 'inherit',
                        fontSize: 16,
                        marginBottom: 12,
                        padding: 14,
                        width: '100%',
                    },
                    value: preferredDate ? preferredDate.toISOString().slice(0, 16) : '',
                    onChange: (event: { target: { value: string } }) => {
                        const date = new Date(`${event.target.value}:00`);
                        setPreferredDate(Number.isNaN(date.getTime()) ? null : date);
                    },
                })
            ) : (
                <>
                    <Pressable style={[styles.dateButton, { borderColor: theme.primary }]} onPress={() => setPickerVisible(true)}>
                        <Text style={{ color: preferredDate ? theme.text : '#999' }}>
                            {preferredDate ? formatDate(preferredDate) : 'Choisir une date et une heure'}
                        </Text>
                    </Pressable>
                    {pickerVisible ? (
                        <DateTimePicker
                            value={preferredDate || new Date()}
                            mode="datetime"
                            minimumDate={new Date()}
                            onChange={handleDateChange}
                        />
                    ) : null}
                </>
            )}
            <TextInput style={[styles.input, { height: 120, borderColor: theme.primary, color: theme.text }]} placeholder="Intentions de messe" placeholderTextColor="#999" value={message} onChangeText={setMessage} multiline />
            <Button title="Envoyer la demande" color={theme.primary} onPress={handleSubmit} />
            {status ? <Text style={[styles.status, { color: theme.text }]}>{status}</Text> : null}
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
        marginBottom: 8,
    },
    helper: {
        color: '#666',
        marginBottom: 12,
    },
    paymentNotice: {
        borderWidth: 1,
        borderRadius: 8,
        padding: 14,
        marginBottom: 14,
    },
    paymentInstruction: {
        fontSize: 16,
        fontWeight: '600',
        marginBottom: 4,
    },
    paymentPhone: {
        fontSize: 18,
        fontWeight: 'bold',
    },
    paymentStatus: {
        fontSize: 14,
    },
    input: {
        borderWidth: 1,
        borderColor: '#ccc',
        borderRadius: 8,
        padding: 12,
        marginBottom: 12,
    },
    fieldLabel: {
        fontWeight: '600',
        marginBottom: 6,
    },
    dateButton: {
        borderWidth: 1,
        borderRadius: 8,
        padding: 14,
        marginBottom: 12,
    },
    status: {
        marginTop: 12,
        color: '#333',
    },
});
