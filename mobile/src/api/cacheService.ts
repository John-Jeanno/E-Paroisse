import AsyncStorage from '@react-native-async-storage/async-storage';

export async function getCachedJson<T>(key: string): Promise<T | null> {
    try {
        const stored = await AsyncStorage.getItem(key);
        return stored ? (JSON.parse(stored) as T) : null;
    } catch {
        return null;
    }
}

export async function setCachedJson<T>(key: string, value: T): Promise<void> {
    try {
        await AsyncStorage.setItem(key, JSON.stringify(value));
    } catch {
        // ignore cache errors
    }
}
