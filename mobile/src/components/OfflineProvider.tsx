import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { AppState, Platform } from 'react-native';
import apiClient from '../api/apiClient';
import { getConnectivity, setConnectivity, subscribeConnectivity } from '../api/connectivityState';
import { getToken, subscribeTokenChanges } from '../api/tokenStorage';
import {
    getFailedMutationCount,
    getQueuedMutations,
    getPendingMutationCount,
    subscribeOutbox,
    synchronizeOutbox,
} from '../api/offlineService';

type PendingAction = {
    id: string;
    label: string;
    status: 'pending' | 'failed';
};

type OfflineStatus = {
    isOnline: boolean;
    pendingCount: number;
    failedCount: number;
    pendingActions: PendingAction[];
    synchronize: () => Promise<void>;
};

const OfflineContext = createContext<OfflineStatus>({
    isOnline: true,
    pendingCount: 0,
    failedCount: 0,
    pendingActions: [],
    synchronize: async () => {},
});

async function prefetchOfflineContent(token: string) {
    const config = { headers: { Authorization: `Token ${token}` } };
    const results = await Promise.allSettled([
        apiClient.get('/annonces/', config),
        apiClient.get('/annonces/fil/', { ...config, params: { page: 1 } }),
        apiClient.get('/auth/profile/', config),
        apiClient.get('/lectures/', config),
        apiClient.get('/lectures/', {
            ...config,
            params: { date: new Date().toISOString().slice(0, 10) },
        }),
        apiClient.get('/messagerie/contacts/', config),
        apiClient.get('/messagerie/entites/', config),
        apiClient.get('/quiz/offline-pack/', config),
    ]);
    let failures = results.filter((result) => result.status === 'rejected').length;
    const contactsResult = results[5];
    const entitiesResult = results[6];
    if (contactsResult.status === 'fulfilled') {
        const contactRequests = (contactsResult.value.data as { id: number }[]).map((contact) =>
            apiClient.get('/messagerie/messages/', {
                ...config,
                params: { contact_id: contact.id, mark_read: false },
            }));
        const contactResults = await Promise.allSettled(contactRequests);
        failures += contactResults.filter((result) => result.status === 'rejected').length;
    }
    if (entitiesResult.status === 'fulfilled') {
        const entityIds = (entitiesResult.value.data as { id: number }[]).map((entity) => entity.id);
        if (entityIds.length > 0) {
            const entityResult = await Promise.allSettled([
                apiClient.get('/messagerie/entites/messages/', {
                    ...config,
                    params: { entity_ids: entityIds, mark_read: false },
                }),
            ]);
            failures += entityResult.filter((result) => result.status === 'rejected').length;
        }
    }
    if (failures > 0) {
        console.warn(`${failures} contenus hors ligne n’ont pas pu être actualisés.`);
    }
}

export function OfflineProvider({ children }: React.PropsWithChildren) {
    const [isOnline, setIsOnline] = useState(getConnectivity() ?? true);
    const [pendingCount, setPendingCount] = useState(0);
    const [failedCount, setFailedCount] = useState(0);
    const [pendingActions, setPendingActions] = useState<PendingAction[]>([]);
    const bootstrapInFlight = useRef(false);

    const refreshPendingCount = useCallback(async () => {
        try {
            setPendingCount(await getPendingMutationCount());
            setFailedCount(await getFailedMutationCount());
            const mutations = await getQueuedMutations();
            setPendingActions(mutations.map((mutation) => {
                const label = mutation.url.includes('/demandes-messe/')
                    ? 'Demander une messe'
                    : mutation.url.includes('/messagerie/messages/')
                        ? 'Message privé'
                        : mutation.url.includes('/messagerie/entites/messages/')
                            ? 'Message de groupe'
                            : mutation.url.includes('/commentaires/')
                                ? 'Commentaire'
                                : mutation.url.endsWith('/j-aime/')
                                    ? 'Réaction à une annonce'
                                    : mutation.url.endsWith('/partager/')
                                        ? 'Partage d’annonce'
                                        : mutation.url.includes('/quiz/offline-results/')
                                            ? 'Résultat du quiz'
                                            : 'Action à synchroniser';
                return { id: mutation.id, label, status: mutation.status };
            }));
        } catch (error) {
            console.error('La file des actions hors ligne n’a pas pu être lue.', error);
        }
    }, []);

    const synchronize = useCallback(async () => {
        if (!isOnline) return;
        await synchronizeOutbox();
        await refreshPendingCount();
    }, [isOnline, refreshPendingCount]);

    const bootstrapAuthenticatedData = useCallback(async () => {
        if (bootstrapInFlight.current) return;
        const token = await getToken();
        if (!token || getConnectivity() === false) return;
        bootstrapInFlight.current = true;
        try {
            await synchronizeOutbox();
            await prefetchOfflineContent(token);
        } finally {
            bootstrapInFlight.current = false;
            await refreshPendingCount();
        }
    }, [refreshPendingCount]);

    useEffect(() => {
        const unsubscribeConnectivity = subscribeConnectivity((value) => setIsOnline(value));
        const unsubscribeOutbox = subscribeOutbox(() => { void refreshPendingCount(); });
        const unsubscribeToken = subscribeTokenChanges((token) => {
            void refreshPendingCount();
            if (token) void bootstrapAuthenticatedData();
        });
        void refreshPendingCount();

        let mounted = true;
        let probeInFlight = false;
        const probe = async () => {
            if (probeInFlight || AppState.currentState !== 'active') return;
            if (Platform.OS === 'web' && typeof navigator !== 'undefined' && !navigator.onLine) {
                setConnectivity(false);
                return;
            }
            probeInFlight = true;
            const controller = new AbortController();
            const timeout = setTimeout(() => controller.abort(), 7000);
            try {
                const response = await fetch(`${apiClient.defaults.baseURL}/`, {
                    method: 'GET',
                    signal: controller.signal,
                });
                if (mounted) setConnectivity(response.status < 500);
            } catch {
                if (mounted) setConnectivity(false);
            } finally {
                clearTimeout(timeout);
                probeInFlight = false;
            }
        };

        void probe();
        const interval = setInterval(() => { void probe(); }, 15000);
        const appStateSubscription = AppState.addEventListener('change', (state) => {
            if (state === 'active') void probe();
        });
        const onOnline = () => { void probe(); };
        const onOffline = () => setConnectivity(false);
        if (Platform.OS === 'web' && typeof window !== 'undefined') {
            window.addEventListener('online', onOnline);
            window.addEventListener('offline', onOffline);
        }

        return () => {
            mounted = false;
            clearInterval(interval);
            appStateSubscription.remove();
            unsubscribeConnectivity();
            unsubscribeOutbox();
            unsubscribeToken();
            if (Platform.OS === 'web' && typeof window !== 'undefined') {
                window.removeEventListener('online', onOnline);
                window.removeEventListener('offline', onOffline);
            }
        };
    }, [bootstrapAuthenticatedData, refreshPendingCount]);

    useEffect(() => {
        if (!isOnline) return;
        void bootstrapAuthenticatedData();
    }, [bootstrapAuthenticatedData, isOnline]);

    const value = useMemo(
        () => ({ isOnline, pendingCount, failedCount, pendingActions, synchronize }),
        [failedCount, isOnline, pendingActions, pendingCount, synchronize],
    );
    return <OfflineContext.Provider value={value}>{children}</OfflineContext.Provider>;
}

export function useOfflineStatus() {
    return useContext(OfflineContext);
}
