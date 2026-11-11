import apiClient from './apiClient';
import { sendOrQueue } from './offlineService';
import { getConnectivity } from './connectivityState';
import { Platform } from 'react-native';

export type MessagingProfile = {
    id: number;
    first_name: string;
    last_name: string;
    group_name?: string;
    parish_entity_names?: string[];
};

export type ParishEntity = {
    id: number;
    name: string;
};

export type PrivateMessage = {
    id: number;
    sender: MessagingProfile;
    recipient: MessagingProfile;
    body: string;
    audio_url?: string | null;
    is_read: boolean;
    created_at: string;
    pending?: boolean;
    syncStatus?: 'pending' | 'failed';
};

export type ParishGroupMessage = {
    id: number;
    entity: ParishEntity;
    sender: MessagingProfile;
    body: string;
    audio_url?: string | null;
    created_at: string;
    pending?: boolean;
    syncStatus?: 'pending' | 'failed';
};

export type UnreadParishEntity = {
    entity_id: number;
    entity_name: string;
    message_count: number;
    sender_name: string;
    body: string;
    created_at: string;
};

export type UnreadPrivateConversation = {
    profile_id: number;
    sender_name: string;
    message_count: number;
    body: string;
    created_at: string;
};

export type MessagingUnreadSummary = {
    private_count: number;
    unread_private_conversations: UnreadPrivateConversation[];
    entity_count: number;
    total_count: number;
    unread_entities: UnreadParishEntity[];
};

export async function fetchMessagingContacts(query = '') {
    if (getConnectivity() === false && query.trim()) {
        const cached = await apiClient.get<MessagingProfile[]>('/messagerie/contacts/');
        const normalizedQuery = query.trim().toLocaleLowerCase();
        return cached.data.filter((contact) => [
            contact.first_name,
            contact.last_name,
            contact.group_name,
            ...(contact.parish_entity_names ?? []),
        ].some((value) => value?.toLocaleLowerCase().includes(normalizedQuery)));
    }
    const response = await apiClient.get<MessagingProfile[]>('/messagerie/contacts/', {
        params: query ? { q: query } : undefined,
    });
    return response.data;
}

export async function fetchPrivateMessages(contactId?: number) {
    const response = await apiClient.get<PrivateMessage[]>('/messagerie/messages/', {
        params: contactId
            ? {
                contact_id: contactId,
                ...(getConnectivity() === false ? { mark_read: false } : {}),
            }
            : undefined,
    });
    return response.data;
}

export async function sendPrivateMessage(recipientId: number, body: string, audioUri?: string) {
    if (audioUri) {
        const formData = await createVoiceFormData(audioUri, {
            recipient_id: String(recipientId),
            body,
        });
        const response = await apiClient.post<PrivateMessage>('/messagerie/messages/', formData, {
            headers: Platform.OS === 'web' ? undefined : { 'Content-Type': 'multipart/form-data' },
        });
        return { data: response.data, queued: false };
    }

    const data = { recipient_id: recipientId, body };
    return sendOrQueue<PrivateMessage>(
        { method: 'post', url: '/messagerie/messages/', data },
        () => ({
            id: -Date.now(),
            sender: { id: -1, first_name: 'Vous', last_name: '' },
            recipient: { id: recipientId, first_name: '', last_name: '' },
            body,
            is_read: false,
            created_at: new Date().toISOString(),
        }),
    );
}

async function createVoiceFormData(uri: string, fields: Record<string, string>) {
    const formData = new FormData();
    Object.entries(fields).forEach(([key, value]) => formData.append(key, value));
    if (Platform.OS === 'web') {
        const blob = await (await fetch(uri)).blob();
        const mimeType = blob.type.toLowerCase().split(';', 1)[0];
        const fileExtension = mimeType === 'audio/mp4' || mimeType === 'audio/m4a'
            ? 'm4a'
            : mimeType.split('/')[1];
        if (![
            'audio/mp4',
            'audio/m4a',
            'audio/webm',
            'audio/ogg',
            'audio/wav',
            'audio/x-wav',
            'audio/mpeg',
            'audio/aac',
        ].includes(mimeType)) {
            throw new Error('Le format audio enregistré n’est pas pris en charge.');
        }
        formData.append('audio', new Blob([blob], { type: mimeType }), `message-vocal.${fileExtension}`);
    } else {
        const fileName = uri.split('/').pop()?.split('?')[0] || 'message-vocal.m4a';
        const extension = fileName.split('.').pop()?.toLowerCase();
        const mimeTypeByExtension: Record<string, string> = {
            m4a: 'audio/mp4',
            mp4: 'audio/mp4',
            aac: 'audio/aac',
            mp3: 'audio/mpeg',
            ogg: 'audio/ogg',
            webm: 'audio/webm',
            wav: 'audio/wav',
        };
        const mimeType = extension ? mimeTypeByExtension[extension] : undefined;
        if (!mimeType) {
            throw new Error('Le format audio enregistré n’est pas pris en charge.');
        }
        // @ts-expect-error React Native FormData accepts a local file URI descriptor.
        formData.append('audio', {
            uri,
            name: fileName,
            type: mimeType,
        });
    }
    return formData;
}

export async function fetchParishEntities() {
    const response = await apiClient.get<ParishEntity[]>('/messagerie/entites/');
    return response.data;
}

export async function fetchParishGroupMessages(entityIds?: number[]) {
    const response = await apiClient.get<ParishGroupMessage[]>('/messagerie/entites/messages/', {
        params: entityIds?.length
            ? {
                entity_ids: entityIds,
                ...(getConnectivity() === false ? { mark_read: false } : {}),
            }
            : undefined,
    });
    return response.data;
}

export async function fetchMessagingUnreadSummary() {
    const response = await apiClient.get<MessagingUnreadSummary>('/messagerie/non-lus/');
    return response.data;
}

export async function sendParishGroupMessage(entityIds: number[], body: string, audioUri?: string) {
    if (audioUri) {
        const formData = await createVoiceFormData(audioUri, { body });
        entityIds.forEach((entityId) => formData.append('entity_ids', String(entityId)));
        const response = await apiClient.post<ParishGroupMessage[]>('/messagerie/entites/messages/', formData, {
            headers: Platform.OS === 'web' ? undefined : { 'Content-Type': 'multipart/form-data' },
        });
        return { data: response.data, queued: false };
    }

    const data = { entity_ids: entityIds, body };
    return sendOrQueue<ParishGroupMessage[]>(
        { method: 'post', url: '/messagerie/entites/messages/', data },
        () => entityIds.map((entityId) => ({
            id: -Date.now() - entityId,
            entity: { id: entityId, name: '' },
            sender: { id: -1, first_name: 'Vous', last_name: '' },
            body,
            created_at: new Date().toISOString(),
        })),
    );
}