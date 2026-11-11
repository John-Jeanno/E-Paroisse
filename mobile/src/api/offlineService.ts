import type { AxiosRequestConfig } from 'axios';
import apiClient from './apiClient';
import { getConnectivity } from './connectivityState';
import { getToken } from './tokenStorage';
import {
    createOperationId,
    getOfflineAccountKey,
    readOutbox,
    QueuedMutation,
    writeOutbox,
} from './offlineStorage';

type OfflineMutationConfig = Pick<AxiosRequestConfig, 'method' | 'url' | 'data' | 'headers'>;

const listeners = new Set<() => void>();
let synchronizing = false;
let outboxWriteQueue: Promise<void> = Promise.resolve();

function withOutboxWriteLock<T>(operation: () => Promise<T>): Promise<T> {
    const result = outboxWriteQueue.then(operation, operation);
    outboxWriteQueue = result.then(() => undefined, () => undefined);
    return result;
}

async function removeMutation(accountKey: string, id: string) {
    await withOutboxWriteLock(async () => {
        const outbox = await readOutbox(accountKey);
        await writeOutbox(accountKey, outbox.filter((mutation) => mutation.id !== id));
    });
}

function notifyOutboxChanged() {
    listeners.forEach((listener) => listener());
}

export function subscribeOutbox(listener: () => void) {
    listeners.add(listener);
    return () => {
        listeners.delete(listener);
    };
}

async function currentAccountKey() {
    return getOfflineAccountKey(await getToken());
}

export async function getPendingMutationCount() {
    const accountKey = await currentAccountKey();
    return (await readOutbox(accountKey)).length;
}

export async function getFailedMutationCount() {
    const accountKey = await currentAccountKey();
    return (await readOutbox(accountKey)).filter((mutation) => mutation.status === 'failed').length;
}

export async function getQueuedMutations(urlPrefix?: string) {
    const accountKey = await currentAccountKey();
    const outbox = await readOutbox(accountKey);
    return urlPrefix
        ? outbox.filter((mutation) => mutation.url.startsWith(urlPrefix))
        : outbox;
}

export async function retryFailedMutations() {
    const accountKey = await currentAccountKey();
    await withOutboxWriteLock(async () => {
        const outbox = await readOutbox(accountKey);
        await writeOutbox(accountKey, outbox.map((mutation) => mutation.status === 'failed'
            ? { ...mutation, status: 'pending', error: undefined }
            : mutation));
    });
    notifyOutboxChanged();
}

async function enqueueMutation(accountKey: string, mutation: QueuedMutation) {
    if (accountKey === 'public') {
        throw new Error('Connectez-vous avant de mettre une action en attente.');
    }
    await withOutboxWriteLock(async () => {
        const outbox = await readOutbox(accountKey);
        if (!outbox.some((item) => item.id === mutation.id)) {
            await writeOutbox(accountKey, [...outbox, mutation]);
        }
    });
    notifyOutboxChanged();
}

export async function sendOrQueue<T>(
    request: OfflineMutationConfig,
    optimisticResult: (operationId: string) => T,
): Promise<{ data: T; queued: boolean }> {
    const token = await getToken();
    const accountKey = getOfflineAccountKey(token);
    const operationId = createOperationId();
    const method = (request.method ?? 'post').toLowerCase() as QueuedMutation['method'];
    const url = request.url;
    if (!url || !['post', 'put', 'patch', 'delete'].includes(method)) {
        throw new Error('Cette action ne peut pas être mise en attente hors ligne.');
    }
    const mutation: QueuedMutation = {
        id: operationId,
        method,
        url,
        data: request.data,
        createdAt: new Date().toISOString(),
        status: 'pending',
    };

    await enqueueMutation(accountKey, mutation);
    if (getConnectivity() === false) {
        return { data: optimisticResult(operationId), queued: true };
    }

    try {
        const response = await apiClient.request<T>({
            ...request,
            method,
            headers: {
                ...request.headers,
                ...(token ? { Authorization: `Token ${token}` } : {}),
                'Idempotency-Key': operationId,
            },
        });
        await removeMutation(accountKey, operationId);
        notifyOutboxChanged();
        return { data: response.data, queued: false };
    } catch (error: unknown) {
        const status = (error as { response?: { status?: number } })?.response?.status;
        if (status !== undefined && status < 500) {
            await removeMutation(accountKey, operationId);
            notifyOutboxChanged();
            throw error;
        }

        return { data: optimisticResult(operationId), queued: true };
    }
}

export async function synchronizeOutbox() {
    if (synchronizing) return;
    const token = await getToken();
    if (!token) return;
    const accountKey = getOfflineAccountKey(token);
    synchronizing = true;
    try {
        const outbox = await readOutbox(accountKey);
        for (const mutation of outbox) {
            if (mutation.status === 'failed') continue;
            if (getOfflineAccountKey(await getToken()) !== accountKey) return;
            try {
                await apiClient.request({
                    method: mutation.method,
                    url: mutation.url,
                    data: mutation.data,
                    headers: {
                        Authorization: `Token ${token}`,
                        'Idempotency-Key': mutation.id,
                    },
                });
                await removeMutation(accountKey, mutation.id);
                notifyOutboxChanged();
            } catch (error: unknown) {
                const status = (error as { response?: { status?: number } })?.response?.status;
                if (status === undefined || status >= 500) break;
                await withOutboxWriteLock(async () => {
                    const current = await readOutbox(accountKey);
                    await writeOutbox(accountKey, current.map((item) => item.id === mutation.id
                        ? { ...item, status: 'failed', error: `Erreur serveur ${status}` }
                        : item));
                });
                notifyOutboxChanged();
            }
        }
    } finally {
        synchronizing = false;
    }
}
