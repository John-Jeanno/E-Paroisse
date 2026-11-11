import * as SecureStore from 'expo-secure-store';

const isWeb = typeof window !== 'undefined' && typeof window.localStorage !== 'undefined';
const tokenListeners = new Set<(token: string | null) => void>();

function notifyTokenChanged(token: string | null) {
    tokenListeners.forEach((listener) => listener(token));
}

export function subscribeTokenChanges(listener: (token: string | null) => void) {
    tokenListeners.add(listener);
    return () => tokenListeners.delete(listener);
}

export async function getToken() {
    if (isWeb) {
        return window.localStorage.getItem('userToken');
    }
    return SecureStore.getItemAsync('userToken');
}

export async function setToken(token: string) {
    if (isWeb) {
        window.localStorage.setItem('userToken', token);
        return;
    }
    await SecureStore.setItemAsync('userToken', token);
    notifyTokenChanged(token);
}

export async function clearToken() {
    if (isWeb) {
        window.localStorage.removeItem('userToken');
        notifyTokenChanged(null);
        return;
    }
    await SecureStore.deleteItemAsync('userToken');
    notifyTokenChanged(null);
}