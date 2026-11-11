import AsyncStorage from '@react-native-async-storage/async-storage';

const CACHE_PREFIX = 'offline-cache-v1';
const OUTBOX_PREFIX = 'offline-outbox-v1';
const DRAFT_PREFIX = 'offline-draft-v1';

export type QueuedMutation = {
    id: string;
    method: 'post' | 'put' | 'patch' | 'delete';
    url: string;
    data?: unknown;
    createdAt: string;
    status: 'pending' | 'failed';
    error?: string;
};

function hash(value: string) {
    let result = 2166136261;
    for (let index = 0; index < value.length; index += 1) {
        result ^= value.charCodeAt(index);
        result = Math.imul(result, 16777619);
    }
    return (result >>> 0).toString(36);
}

export function getOfflineAccountKey(token?: string | null) {
    return token ? hash(token) : 'public';
}

export function getApiCacheKey(token: string | null, url: string) {
    return `${CACHE_PREFIX}:${getOfflineAccountKey(token)}:${hash(url)}`;
}

function offlineDraftKey(token: string | null, draftId: string) {
    return `${DRAFT_PREFIX}:${getOfflineAccountKey(token)}:${hash(draftId)}`;
}

export async function readOfflineDraft<T>(token: string | null, draftId: string): Promise<T | null> {
    const stored = await AsyncStorage.getItem(offlineDraftKey(token, draftId));
    return stored ? JSON.parse(stored) as T : null;
}

export async function writeOfflineDraft(token: string | null, draftId: string, value: unknown) {
    const key = offlineDraftKey(token, draftId);
    if (value === null) {
        await AsyncStorage.removeItem(key);
        return;
    }
    await AsyncStorage.setItem(key, JSON.stringify(value));
}

export async function readApiCache<T>(key: string): Promise<T | null> {
    const stored = await AsyncStorage.getItem(key);
    return stored ? JSON.parse(stored) as T : null;
}

export async function writeApiCache(key: string, value: unknown) {
    await AsyncStorage.setItem(key, JSON.stringify(value));
}

function outboxKey(accountKey: string) {
    return `${OUTBOX_PREFIX}:${accountKey}`;
}

export async function readOutbox(accountKey: string): Promise<QueuedMutation[]> {
    const stored = await AsyncStorage.getItem(outboxKey(accountKey));
    if (!stored) return [];
    const parsed: unknown = JSON.parse(stored);
    if (!Array.isArray(parsed)) {
        throw new Error('La file hors ligne est illisible. Les données locales ne seront pas supprimées.');
    }
    return parsed as QueuedMutation[];
}

export async function writeOutbox(accountKey: string, mutations: QueuedMutation[]) {
    const key = outboxKey(accountKey);
    if (mutations.length === 0) {
        await AsyncStorage.removeItem(key);
        return;
    }
    await AsyncStorage.setItem(key, JSON.stringify(mutations));
}

export async function removeOutboxMutation(accountKey: string, id: string) {
    const mutations = await readOutbox(accountKey);
    await writeOutbox(accountKey, mutations.filter((item) => item.id !== id));
}

export function createOperationId() {
    const randomUUID = globalThis.crypto?.randomUUID?.bind(globalThis.crypto);
    return randomUUID
        ? randomUUID()
        : `${Date.now()}-${Math.random().toString(36).slice(2)}-${Math.random().toString(36).slice(2)}`;
}
