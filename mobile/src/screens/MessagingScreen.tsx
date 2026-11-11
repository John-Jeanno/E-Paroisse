import React, { useCallback, useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import {
    ActivityIndicator,
    FlatList,
    KeyboardAvoidingView,
    Platform,
    Pressable,
    ScrollView,
    StyleSheet,
    Text,
    TextInput,
    View,
} from 'react-native';
import Svg, { Path } from 'react-native-svg';
import {
    RecordingPresets,
    requestRecordingPermissionsAsync,
    setAudioModeAsync,
    useAudioRecorder,
    useAudioRecorderState,
} from 'expo-audio';
import { useFocusEffect } from '@react-navigation/native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import {
    fetchMessagingContacts,
    fetchParishEntities,
    fetchParishGroupMessages,
    fetchPrivateMessages,
    MessagingProfile,
    ParishEntity,
    ParishGroupMessage,
    PrivateMessage,
    sendParishGroupMessage,
    sendPrivateMessage,
} from '../api/messagingService';
import { getQueuedMutations, subscribeOutbox } from '../api/offlineService';
import { readOfflineDraft, writeOfflineDraft } from '../api/offlineStorage';
import { getToken } from '../api/tokenStorage';
import { getConnectivity } from '../api/connectivityState';
import VoiceMessagePlayer from '../components/VoiceMessagePlayer';
import { useTheme } from '../theme/LiturgicalTheme';
import useResponsiveLayout from '../hooks/useResponsiveLayout';
import type { RootStackParamList } from '../navigation/AppNavigator';

type Props = NativeStackScreenProps<RootStackParamList, 'Messaging'>;
type ConversationType = 'person' | 'entity';
type MessagingErrorResponse = {
    detail?: string;
    body?: string[];
    entity_ids?: string[];
    recipient_id?: string[];
};
type QueuedMessageData = {
    body?: string;
    recipient_id?: number;
    entity_ids?: number[];
};

const profileName = (profile: MessagingProfile) =>
    `${profile.first_name} ${profile.last_name}`.trim() || 'Paroissien';

function getSendErrorMessage(error: unknown) {
    if (axios.isAxiosError<MessagingErrorResponse>(error)) {
        const response = error.response?.data;
        const detail = response?.detail
            ?? response?.entity_ids?.[0]
            ?? response?.body?.[0]
            ?? response?.recipient_id?.[0];
        if (detail) return detail;
    }
    return 'Échec de l’envoi du message. Vérifiez votre connexion puis réessayez.';
}

export default function MessagingScreen({ route }: Props) {
    const theme = useTheme();
    const { contentMaxWidth, horizontalPadding } = useResponsiveLayout();
    const [conversationType, setConversationType] = useState<ConversationType>('person');
    const [contacts, setContacts] = useState<MessagingProfile[]>([]);
    const [entities, setEntities] = useState<ParishEntity[]>([]);
    const [privateMessages, setPrivateMessages] = useState<PrivateMessage[]>([]);
    const [entityMessages, setEntityMessages] = useState<ParishGroupMessage[]>([]);
    const [recipient, setRecipient] = useState<MessagingProfile | null>(null);
    const [selectedEntityIds, setSelectedEntityIds] = useState<number[]>([]);
    const [contactQuery, setContactQuery] = useState('');
    const [body, setBody] = useState('');
    const [recordedAudioUri, setRecordedAudioUri] = useState<string | null>(null);
    const [recordedAudioDuration, setRecordedAudioDuration] = useState(0);
    const [status, setStatus] = useState('');
    const [loadingContacts, setLoadingContacts] = useState(false);
    const [sendingVoice, setSendingVoice] = useState(false);
    const recorder = useAudioRecorder(RecordingPresets.HIGH_QUALITY);
    const recorderState = useAudioRecorderState(recorder, 250);
    const finishingRecording = React.useRef(false);
    const messagesScrollRef = React.useRef<ScrollView>(null);
    const [loadedDraftId, setLoadedDraftId] = useState<string | null>(null);
    const draftId = useMemo(
        () => conversationType === 'person'
            ? `message-composer-person-${recipient?.id ?? route.params?.contactId ?? 'new'}`
            : `message-composer-entities-${[...selectedEntityIds].sort((a, b) => a - b).join('-') || 'none'}`,
        [conversationType, recipient?.id, route.params?.contactId, selectedEntityIds],
    );

    useEffect(() => {
        let active = true;
        setLoadedDraftId(null);
        setBody('');
        void getToken()
            .then((token) => readOfflineDraft<string>(token, draftId))
            .then((draft) => {
                if (!active) return;
                setBody(draft ?? '');
                setLoadedDraftId(draftId);
            })
            .catch((error: unknown) => {
                console.error('Le brouillon du message n’a pas pu être restauré.', error);
                if (active) setLoadedDraftId(draftId);
            });
        return () => { active = false; };
    }, [draftId]);

    useEffect(() => {
        if (loadedDraftId !== draftId) return undefined;
        const timeout = setTimeout(() => {
            void getToken()
                .then((token) => writeOfflineDraft(token, draftId, body || null))
                .catch((error: unknown) => {
                    console.error('Le brouillon du message n’a pas pu être enregistré.', error);
                });
        }, 250);
        return () => clearTimeout(timeout);
    }, [body, draftId, loadedDraftId]);

    const loadMessages = useCallback(async () => {
        const [privateResult, entityResult, queuedResult] = await Promise.allSettled([
            fetchPrivateMessages(recipient?.id ?? route.params?.contactId),
            fetchParishGroupMessages(selectedEntityIds),
            getQueuedMutations('/messagerie/'),
        ]);
        if (privateResult.status === 'rejected' || entityResult.status === 'rejected') {
            setStatus('Impossible d’actualiser certains messages. Les données locales restent affichées.');
        }

        const queued = queuedResult.status === 'fulfilled' ? queuedResult.value : [];
        const privatePending: PrivateMessage[] = queued
            .filter((mutation) => mutation.url === '/messagerie/messages/')
            .map((mutation, index) => {
                const data = mutation.data as QueuedMessageData;
                return {
                    id: -(index + 1),
                    sender: { id: -1, first_name: 'Vous', last_name: '' },
                    recipient: { id: data.recipient_id ?? 0, first_name: '', last_name: '' },
                    body: data.body ?? '',
                    is_read: false,
                    created_at: mutation.createdAt,
                    pending: true,
                    syncStatus: mutation.status,
                };
            })
            .filter((message) =>
                !recipient && !route.params?.contactId
                    ? false
                    : message.recipient.id === (recipient?.id ?? route.params?.contactId));
        const entityPending: ParishGroupMessage[] = queued
            .filter((mutation) => mutation.url === '/messagerie/entites/messages/')
            .flatMap((mutation, index) => {
                const data = mutation.data as QueuedMessageData;
                return (data.entity_ids ?? [])
                    .filter((entityId) => selectedEntityIds.includes(entityId))
                    .map((entityId, entityIndex) => ({
                        id: -((index + 1) * 1000 + entityIndex),
                        entity: entities.find((entity) => entity.id === entityId) ?? { id: entityId, name: '' },
                        sender: { id: -1, first_name: 'Vous', last_name: '' },
                        body: data.body ?? '',
                        created_at: mutation.createdAt,
                        pending: true,
                        syncStatus: mutation.status,
                    }));
            });
        const privateItems = privateResult.status === 'fulfilled' ? privateResult.value : [];
        const entityItems = entityResult.status === 'fulfilled' ? entityResult.value : [];
        setPrivateMessages([...privateItems, ...privatePending].sort((a, b) =>
            b.created_at.localeCompare(a.created_at)));
        setEntityMessages([...entityItems, ...entityPending].sort((a, b) =>
            b.created_at.localeCompare(a.created_at)));
        if (!recipient && route.params?.contactId && privateItems.length > 0) {
            const firstMessage = privateItems[0];
            setRecipient(
                firstMessage.sender.id === route.params.contactId
                    ? firstMessage.sender
                    : firstMessage.recipient,
            );
        }
    }, [entities, recipient, route.params?.contactId, selectedEntityIds]);

    useFocusEffect(
        useCallback(() => {
            void loadMessages();
            const interval = setInterval(() => void loadMessages(), 15000);
            const unsubscribeOutbox = subscribeOutbox(() => { void loadMessages(); });
            return () => {
                clearInterval(interval);
                unsubscribeOutbox();
            };
        }, [loadMessages]),
    );

    useEffect(() => {
        let current = true;
        fetchParishEntities()
            .then((items) => {
                if (current) {
                    setEntities(items);
                    if (route.params?.entityId) {
                        setSelectedEntityIds([route.params.entityId]);
                        setConversationType('entity');
                    }
                }
            })
            .catch(() => {
                if (current) setStatus('Impossible de charger les entités paroissiales.');
            });
        return () => {
            current = false;
        };
    }, [route.params?.entityId]);

    useEffect(() => {
        let current = true;
        const query = contactQuery.trim();
        if (query.length === 1) {
            setContacts([]);
            return () => {
                current = false;
            };
        }
        const timeout = setTimeout(() => {
            setLoadingContacts(true);
            fetchMessagingContacts(query)
                .then((items) => {
                    if (current) setContacts(items);
                })
                .catch(() => {
                    if (current) setStatus('Impossible de rechercher les utilisateurs.');
                })
                .finally(() => {
                    if (current) setLoadingContacts(false);
                });
        }, query ? 250 : 0);
        return () => {
            current = false;
            clearTimeout(timeout);
        };
    }, [contactQuery]);

    useEffect(() => {
        const selectedContact = contacts.find((contact) => contact.id === route.params?.contactId);
        if (selectedContact) {
            setRecipient(selectedContact);
            setConversationType('person');
        }
    }, [contacts, route.params?.contactId]);

    const handleSend = async () => {
        if (conversationType === 'person' && !recipient) {
            setStatus('Recherchez puis sélectionnez un destinataire.');
            return;
        }
        if (conversationType === 'entity' && selectedEntityIds.length === 0) {
            setStatus('Sélectionnez au moins une entité paroissiale.');
            return;
        }
        const messageText = body.trim();
        const audioUri = recordedAudioUri;
        if (!messageText && !audioUri) {
            setStatus('Écrivez un message ou enregistrez un vocal avant de l’envoyer.');
            return;
        }
        if (audioUri && getConnectivity() === false) {
            setStatus('Connectez-vous à Internet pour envoyer le message vocal.');
            return;
        }

        if (audioUri) setSendingVoice(true);
        try {
            if (conversationType === 'person' && recipient) {
                const result = await sendPrivateMessage(recipient.id, messageText, audioUri ?? undefined);
                setStatus(result.queued
                    ? `Message enregistré sur cet appareil. Il sera envoyé à ${profileName(recipient)} au retour du réseau.`
                    : `Message${audioUri ? ' vocal' : ''} envoyé à ${profileName(recipient)}.`);
            } else if (conversationType === 'entity' && selectedEntityIds.length > 0) {
                const result = await sendParishGroupMessage(selectedEntityIds, messageText, audioUri ?? undefined);
                const selectedEntityNames = entities
                    .filter((entity) => selectedEntityIds.includes(entity.id))
                    .map((entity) => entity.name);
                setStatus(result.queued
                    ? `Message enregistré sur cet appareil. Il sera envoyé à ${selectedEntityNames.join(', ')} au retour du réseau.`
                    : `Message${audioUri ? ' vocal' : ''} envoyé à ${selectedEntityNames.join(', ')}.`);
            }
            setBody('');
            if (audioUri?.startsWith('blob:')) URL.revokeObjectURL(audioUri);
            setRecordedAudioUri(null);
            setRecordedAudioDuration(0);
            await loadMessages();
        } catch (error: unknown) {
            setStatus(getSendErrorMessage(error));
        } finally {
            if (audioUri) setSendingVoice(false);
        }
    };

    const finishVoiceRecording = useCallback(async () => {
        if (finishingRecording.current || !recorder.isRecording) return;
        finishingRecording.current = true;
        setSendingVoice(true);
        try {
            const duration = recorderState.durationMillis;
            await recorder.stop();
            await setAudioModeAsync({ allowsRecording: false, playsInSilentMode: true });
            const uri = recorder.uri;
            if (!uri) throw new Error('Le fichier vocal n’a pas pu être préparé.');
            if (recordedAudioUri?.startsWith('blob:')) URL.revokeObjectURL(recordedAudioUri);
            setRecordedAudioUri(uri);
            setRecordedAudioDuration(duration);
            setStatus('Vocal prêt à être écouté puis envoyé.');
        } catch (error: unknown) {
            setStatus(getSendErrorMessage(error));
        } finally {
            finishingRecording.current = false;
            setSendingVoice(false);
        }
    }, [recorder, recorderState.durationMillis, recordedAudioUri]);

    useEffect(() => {
        if (recorderState.isRecording && recorderState.durationMillis >= 120_000) {
            void finishVoiceRecording();
        }
    }, [finishVoiceRecording, recorderState.durationMillis, recorderState.isRecording]);

    const toggleVoiceRecording = async () => {
        if (recorderState.isRecording) {
            await finishVoiceRecording();
            return;
        }
        if (getConnectivity() === false) {
            setStatus('Les messages vocaux nécessitent une connexion Internet.');
            return;
        }
        if (conversationType === 'person' && !recipient) {
            setStatus('Sélectionnez un destinataire avant d’enregistrer un vocal.');
            return;
        }
        if (conversationType === 'entity' && selectedEntityIds.length === 0) {
            setStatus('Sélectionnez une entité avant d’enregistrer un vocal.');
            return;
        }
        setSendingVoice(true);
        try {
            const permission = await requestRecordingPermissionsAsync();
            if (!permission.granted) {
                setStatus('Autorisez l’accès au microphone pour enregistrer un message vocal.');
                return;
            }
            await setAudioModeAsync({ allowsRecording: true, playsInSilentMode: true });
            await recorder.prepareToRecordAsync();
            recorder.record();
            if (recordedAudioUri?.startsWith('blob:')) URL.revokeObjectURL(recordedAudioUri);
            setRecordedAudioUri(null);
            setRecordedAudioDuration(0);
            setStatus('Enregistrement en cours — maximum 2 minutes.');
        } catch {
            setStatus('Impossible de démarrer l’enregistrement vocal.');
        } finally {
            setSendingVoice(false);
        }
    };

    const selectedPrivateMessages = recipient
        ? privateMessages.filter((message) =>
            message.sender.id === recipient.id || message.recipient.id === recipient.id)
        : [];
    const selectedEntityMessages = entityMessages.filter((message) =>
        selectedEntityIds.includes(message.entity.id));
    const selectedEntityNames = entities
        .filter((entity) => selectedEntityIds.includes(entity.id))
        .map((entity) => entity.name);

    const toggleEntity = (entityId: number) => {
        setSelectedEntityIds((selected) => selected.includes(entityId)
            ? selected.filter((id) => id !== entityId)
            : [...selected, entityId]);
    };

    return (
        <KeyboardAvoidingView
            style={{ flex: 1, backgroundColor: theme.background }}
            behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        >
        <View style={[
            styles.container,
            { backgroundColor: theme.background, maxWidth: contentMaxWidth, paddingHorizontal: horizontalPadding },
        ]}>
            <Text style={[styles.title, { color: theme.primary }]}>Messagerie</Text>
            <View style={[styles.modeRow, { borderColor: theme.accent }]}>
                <Pressable
                    accessibilityRole="button"
                    accessibilityState={{ selected: conversationType === 'person' }}
                    disabled={recorderState.isRecording || sendingVoice}
                    onPress={() => setConversationType('person')}
                    style={[styles.modeButton, conversationType === 'person' && { backgroundColor: theme.primary }]}
                >
                    <Text style={[styles.modeButtonText, { color: conversationType === 'person' ? '#fff' : theme.primary }]}>
                        Messages privés
                    </Text>
                </Pressable>
                <Pressable
                    accessibilityRole="button"
                    accessibilityState={{ selected: conversationType === 'entity' }}
                    disabled={recorderState.isRecording || sendingVoice}
                    onPress={() => setConversationType('entity')}
                    style={[styles.modeButton, conversationType === 'entity' && { backgroundColor: theme.primary }]}
                >
                    <Text style={[styles.modeButtonText, { color: conversationType === 'entity' ? '#fff' : theme.primary }]}>
                        Entités paroissiales
                    </Text>
                </Pressable>
            </View>

            {conversationType === 'person' ? (
                <>
                    <Text style={[styles.sectionLabel, { color: theme.text }]}>Rechercher un utilisateur</Text>
                    <TextInput
                        accessibilityLabel="Rechercher un utilisateur"
                        style={[styles.searchInput, { borderColor: theme.accent, color: theme.text, backgroundColor: theme.card }]}
                        placeholder="Prénom, nom ou entité"
                        placeholderTextColor="#999"
                        value={contactQuery}
                        onChangeText={setContactQuery}
                    />
                    {loadingContacts ? <ActivityIndicator color={theme.primary} style={styles.loader} /> : null}
                    <FlatList
                        data={contacts}
                        horizontal
                        keyExtractor={(item) => String(item.id)}
                        style={styles.choices}
                        keyboardShouldPersistTaps="handled"
                        renderItem={({ item }) => {
                            const selected = recipient?.id === item.id;
                            return (
                                <Pressable
                                    accessibilityRole="button"
                                    accessibilityState={{ selected }}
                                    style={[
                                        styles.choice,
                                        { borderColor: theme.primary },
                                        selected && { backgroundColor: theme.primary },
                                    ]}
                                    onPress={() => setRecipient(item)}
                                >
                                    <Text style={{ color: selected ? '#fff' : theme.text }}>{profileName(item)}</Text>
                                    {item.group_name ? (
                                        <Text style={[styles.choiceSubtitle, { color: selected ? '#fff' : theme.text }]}>
                                            {item.group_name}
                                        </Text>
                                    ) : null}
                                </Pressable>
                            );
                        }}
                        ListEmptyComponent={!loadingContacts ? (
                            <Text style={{ color: theme.text }}>Aucun utilisateur trouvé.</Text>
                        ) : null}
                    />
                    <Text style={[styles.recipient, { color: theme.primary }]}>
                        Destinataire : {recipient ? profileName(recipient) : 'aucun'}
                    </Text>
                </>
            ) : (
                <>
                    <Text style={[styles.sectionLabel, { color: theme.text }]}>Entités paroissiales</Text>
                    <Text style={[styles.entityHint, { color: theme.text }]}>
                        Sélectionnez une ou plusieurs entités pour leur envoyer le même message.
                    </Text>
                    <FlatList
                        data={entities}
                        keyExtractor={(item) => String(item.id)}
                        style={styles.choices}
                        numColumns={2}
                        columnWrapperStyle={styles.entityRow}
                        renderItem={({ item }) => {
                            const selected = selectedEntityIds.includes(item.id);
                            return (
                                <Pressable
                                    accessibilityRole="checkbox"
                                    accessibilityState={{ checked: selected }}
                                    style={[
                                        styles.choice,
                                        { borderColor: theme.primary },
                                        selected && { backgroundColor: theme.primary },
                                    ]}
                                    onPress={() => toggleEntity(item.id)}
                                >
                                    <Text style={{ color: selected ? '#fff' : theme.text }}>
                                        {selected ? '✓ ' : '□ '}{item.name}
                                    </Text>
                                </Pressable>
                            );
                        }}
                        ListEmptyComponent={
                            <Text style={{ color: theme.text }}>
                                Aucune entité paroissiale n’est disponible.
                            </Text>
                        }
                    />
                    <Text style={[styles.recipient, { color: theme.primary }]}>
                        Message destiné à : {selectedEntityNames.length ? selectedEntityNames.join(', ') : 'aucune entité'}
                    </Text>
                </>
            )}

            <Text style={[styles.sectionLabel, { color: theme.text }]}>
                {conversationType === 'person'
                    ? 'Conversation privée'
                    : `Messages de ${selectedEntityNames.length ? selectedEntityNames.join(', ') : 'vos entités'}`}
            </Text>
            <ScrollView
                ref={messagesScrollRef}
                style={styles.messages}
                contentContainerStyle={styles.messagesContent}
                onContentSizeChange={() => messagesScrollRef.current?.scrollToEnd({ animated: false })}
            >
                {conversationType === 'person' ? (
                    selectedPrivateMessages.length ? [...selectedPrivateMessages].reverse().map((item) => {
                        const sentByMe = item.sender.id !== recipient?.id;
                        return (
                            <View key={`private-${item.id}`} style={[
                                styles.messageBubble,
                                sentByMe ? styles.sentBubble : styles.receivedBubble,
                                { backgroundColor: sentByMe ? theme.primary : theme.card, borderColor: theme.accent },
                            ]}>
                                <Text style={[styles.cardHeader, { color: sentByMe ? '#fff' : theme.primary }]}>
                                    {sentByMe ? 'Vous' : profileName(item.sender)}
                                </Text>
                                {item.body ? <Text style={{ color: sentByMe ? '#fff' : theme.text }}>{item.body}</Text> : null}
                                {item.audio_url ? <VoiceMessagePlayer audioPath={item.audio_url} /> : null}
                                <Text style={[styles.timestamp, { color: sentByMe ? '#fff' : theme.text }]}>
                                    {new Date(item.created_at).toLocaleString('fr-FR')}{item.pending
                                        ? item.syncStatus === 'failed' ? ' · échec de synchronisation' : ' · en attente'
                                        : ''}
                                </Text>
                            </View>
                        );
                    }) : <Text style={{ color: theme.text }}>Aucun message dans cette conversation.</Text>
                ) : (
                    selectedEntityMessages.length ? [...selectedEntityMessages].reverse().map((item) => (
                        <View key={`entity-${item.id}`} style={[
                            styles.messageBubble,
                            { backgroundColor: theme.card, borderColor: theme.accent },
                        ]}>
                            <Text style={[styles.cardHeader, { color: theme.primary }]}>
                                {profileName(item.sender)} · {item.entity.name}
                            </Text>
                            {item.body ? <Text style={{ color: theme.text }}>{item.body}</Text> : null}
                            {item.audio_url ? <VoiceMessagePlayer audioPath={item.audio_url} /> : null}
                            <Text style={[styles.timestamp, { color: theme.text }]}>
                                {new Date(item.created_at).toLocaleString('fr-FR')}{item.pending
                                    ? item.syncStatus === 'failed' ? ' · échec de synchronisation' : ' · en attente'
                                    : ''}
                            </Text>
                        </View>
                    )) : <Text style={{ color: theme.text }}>Aucun message pour les entités sélectionnées.</Text>
                )}
            </ScrollView>
            <View style={[styles.composer, { borderColor: theme.accent, backgroundColor: theme.card }]}>
                <TextInput
                    accessibilityLabel={conversationType === 'person' ? 'Votre message privé' : 'Votre message à l’entité'}
                    style={[styles.messageInput, { borderColor: theme.accent, color: theme.text }]}
                    placeholder="Écrire un message…"
                    placeholderTextColor="#999"
                    value={body}
                    onChangeText={setBody}
                    multiline
                    editable={!sendingVoice && !recorderState.isRecording}
                />
                <View style={styles.composerActions}>
                    <Pressable
                        accessibilityRole="button"
                        accessibilityLabel={recorderState.isRecording ? 'Arrêter l’enregistrement vocal' : 'Enregistrer un message vocal'}
                        disabled={sendingVoice}
                        onPress={() => void toggleVoiceRecording()}
                        style={[styles.composerButton, { backgroundColor: recorderState.isRecording ? '#b42318' : theme.accent }]}
                    >
                        {sendingVoice
                            ? <ActivityIndicator color="#fff" />
                            : (
                                <>
                                    <Svg width={22} height={22} viewBox="0 0 24 24" fill="none">
                                        {recorderState.isRecording ? (
                                            <Path d="M7 7h10v10H7z" fill="#fff" />
                                        ) : (
                                            <>
                                                <Path d="M12 3a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3Z" stroke="#fff" strokeWidth={2} />
                                                <Path d="M19 11a7 7 0 0 1-14 0M12 18v3m-4 0h8" stroke="#fff" strokeWidth={2} strokeLinecap="round" />
                                            </>
                                        )}
                                    </Svg>
                                    {recorderState.isRecording ? (
                                        <Text style={styles.composerButtonText}>{Math.floor(recorderState.durationMillis / 1000)}s</Text>
                                    ) : null}
                                </>
                            )}
                    </Pressable>
                    <Pressable
                        accessibilityRole="button"
                        accessibilityLabel="Envoyer le message"
                        disabled={sendingVoice || recorderState.isRecording || (!body.trim() && !recordedAudioUri)}
                        onPress={() => void handleSend()}
                        style={[styles.composerButton, { backgroundColor: theme.primary }]}
                    >
                        <Text style={styles.composerButtonText}>Envoyer</Text>
                    </Pressable>
                </View>
            </View>
            {recordedAudioUri ? (
                <View style={[styles.voiceDraft, { borderColor: theme.accent, backgroundColor: theme.card }]}>
                    <Text style={{ color: theme.text, fontWeight: '700' }}>
                        Aperçu du vocal · {Math.max(1, Math.ceil(recordedAudioDuration / 1000))} s
                    </Text>
                    <VoiceMessagePlayer audioPath={recordedAudioUri} />
                    <Pressable
                        accessibilityRole="button"
                        accessibilityLabel="Supprimer le vocal enregistré"
                        onPress={() => {
                            if (recordedAudioUri.startsWith('blob:')) URL.revokeObjectURL(recordedAudioUri);
                            setRecordedAudioUri(null);
                            setRecordedAudioDuration(0);
                            setStatus('');
                        }}
                    >
                        <Text style={{ color: '#b42318', fontWeight: '700' }}>Supprimer</Text>
                    </Pressable>
                </View>
            ) : null}
            {status ? <Text style={[styles.status, { color: theme.text }]}>{status}</Text> : null}
        </View>
        </KeyboardAvoidingView>
    );
}

const styles = StyleSheet.create({
    container: { flex: 1, width: '100%', alignSelf: 'center', padding: 24, paddingBottom: 8 },
    title: { fontSize: 22, fontWeight: 'bold', marginBottom: 14 },
    modeRow: { flexDirection: 'row', borderWidth: 1, borderRadius: 10, overflow: 'hidden', marginBottom: 12 },
    modeButton: { flex: 1, paddingVertical: 11, paddingHorizontal: 8, alignItems: 'center' },
    modeButtonText: { fontSize: 13, fontWeight: '700', textAlign: 'center' },
    sectionLabel: { fontSize: 16, fontWeight: '700', marginBottom: 8, marginTop: 8 },
    searchInput: { borderWidth: 1, borderRadius: 10, padding: 11, marginBottom: 8 },
    loader: { marginVertical: 8 },
    choices: { flexGrow: 0, minHeight: 44, maxHeight: 190, marginBottom: 8 },
    entityRow: { gap: 8 },
    entityHint: { fontSize: 13, marginBottom: 8, opacity: 0.8 },
    choice: { borderWidth: 1, borderRadius: 10, paddingVertical: 9, paddingHorizontal: 12, marginRight: 8, marginBottom: 8, justifyContent: 'center', flex: 1 },
    choiceSubtitle: { fontSize: 11, opacity: 0.8, marginTop: 2 },
    recipient: { marginBottom: 8, fontWeight: '600' },
    messageInput: { flex: 1, borderWidth: 1, borderRadius: 18, minHeight: 44, maxHeight: 100, paddingHorizontal: 14, paddingVertical: 10, textAlignVertical: 'top' },
    messages: { flex: 1, minHeight: 120, marginTop: 6, borderRadius: 16 },
    messagesContent: { paddingHorizontal: 4, paddingVertical: 12 },
    messageBubble: { width: '82%', borderWidth: 1, borderRadius: 16, padding: 12, marginBottom: 10 },
    sentBubble: { alignSelf: 'flex-end', borderBottomRightRadius: 4 },
    receivedBubble: { alignSelf: 'flex-start', borderBottomLeftRadius: 4 },
    composer: { flexDirection: 'row', alignItems: 'flex-end', gap: 8, borderWidth: 1, borderRadius: 20, padding: 8, marginTop: 8 },
    composerActions: { gap: 6, alignItems: 'center' },
    composerButton: { minWidth: 52, minHeight: 48, borderRadius: 14, paddingHorizontal: 8, alignItems: 'center', justifyContent: 'center' },
    composerButtonText: { color: '#fff', fontSize: 13, fontWeight: '700' },
    voiceDraft: { gap: 10, flexDirection: 'row', alignItems: 'center', borderWidth: 1, borderRadius: 14, padding: 10, marginTop: 8, flexWrap: 'wrap' },
    cardHeader: { fontWeight: '700', marginBottom: 8 },
    timestamp: { fontSize: 12, marginTop: 8, opacity: 0.7 },
    status: { marginTop: 8 },
});
