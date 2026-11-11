import axios, { type InternalAxiosRequestConfig } from 'axios';
import Constants from 'expo-constants';
import { getToken } from './tokenStorage';
import { setConnectivity } from './connectivityState';
import { getApiCacheKey, readApiCache, writeApiCache } from './offlineStorage';

const API_PORT = process.env.EXPO_PUBLIC_API_PORT ?? '8000';
const API_URL = process.env.EXPO_PUBLIC_API_URL;
const PRODUCTION_API_URL = 'https://5szq.l.time4vps.cloud:18080/api';

const getApiHost = () => {
    if (typeof window !== 'undefined' && window.location.hostname) {
        const browserHost = window.location.hostname;
        return browserHost;
    }

    const expoConfigHost =
        typeof Constants.expoConfig?.hostUri === 'string'
            ? Constants.expoConfig.hostUri
            : typeof Constants.expoConfig?.extra?.expoGo?.hostUri === 'string'
                ? Constants.expoConfig.extra.expoGo.hostUri
                : undefined;

    const manifestHost =
        typeof Constants.manifest?.debuggerHost === 'string'
            ? Constants.manifest.debuggerHost
            : undefined;
    const hostUri = expoConfigHost ?? manifestHost;

    if (hostUri) {
        return hostUri.split(':')[0];
    }

    return process.env.EXPO_PUBLIC_API_HOST ?? '127.0.0.1';
};

const getApiBaseUrl = () => {
    if (API_URL) {
        return API_URL;
    }

    if (typeof window !== 'undefined' && window.location.hostname) {
        if (window.location.protocol === 'https:') {
            return `${window.location.origin}/api`;
        }
        return `http://${getApiHost()}:${API_PORT}/api`;
    }

    if (__DEV__) {
        return `http://${getApiHost()}:${API_PORT}/api`;
    }

    return PRODUCTION_API_URL;
};

const apiClient = axios.create({
    baseURL: getApiBaseUrl(),
    timeout: 10000,
});

type OfflineAwareRequestConfig = InternalAxiosRequestConfig & {
    offlineAccountToken?: string | null;
};

apiClient.interceptors.request.use(async (config) => {
    const authorization = config.headers.Authorization;
    const token = typeof authorization === 'string' && authorization.startsWith('Token ')
        ? authorization.slice('Token '.length)
        : await getToken();
    (config as OfflineAwareRequestConfig).offlineAccountToken = token;
    if (!authorization) {
        if (token) {
            config.headers.Authorization = `Token ${token}`;
        }
    }
    return config;
});

apiClient.interceptors.response.use(
    async (response) => {
        setConnectivity(true);
        if (response.config.method?.toLowerCase() === 'get') {
            try {
                const requestConfig = response.config as OfflineAwareRequestConfig;
                const token = requestConfig.offlineAccountToken !== undefined
                    ? requestConfig.offlineAccountToken
                    : await getToken();
                const key = getApiCacheKey(token, apiClient.getUri(response.config));
                await writeApiCache(key, response.data);
            } catch (error) {
                console.warn('Impossible de mettre cette réponse en cache hors ligne.', error);
            }
        }
        return response;
    },
    async (error: unknown) => {
        const requestError = error as {
            config?: InternalAxiosRequestConfig;
            response?: { status?: number; headers?: Record<string, string>; data?: unknown };
        };
        if (requestError.response) {
            setConnectivity(true);
            return Promise.reject(error);
        }

        setConnectivity(false);
        const config = requestError.config;
        if (!config || config.method?.toLowerCase() !== 'get') {
            return Promise.reject(error);
        }

        try {
            const requestConfig = config as OfflineAwareRequestConfig;
            const token = requestConfig.offlineAccountToken !== undefined
                ? requestConfig.offlineAccountToken
                : await getToken();
            const key = getApiCacheKey(token, apiClient.getUri(config));
            const data = await readApiCache(key);
            if (data !== null) {
                return {
                    config,
                    data,
                    headers: { 'x-offline-cache': 'true' },
                    status: 200,
                    statusText: 'Offline cache',
                };
            }
        } catch (cacheError) {
            console.warn('Impossible de lire le cache hors ligne.', cacheError);
        }
        return Promise.reject(error);
    },
);

export default apiClient;
