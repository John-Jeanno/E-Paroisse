let connected: boolean | null = null;
const listeners = new Set<(value: boolean) => void>();

export function setConnectivity(value: boolean) {
    if (connected === value) return;
    connected = value;
    listeners.forEach((listener) => listener(value));
}

export function getConnectivity() {
    return connected;
}

export function subscribeConnectivity(listener: (value: boolean) => void) {
    listeners.add(listener);
    if (connected !== null) listener(connected);
    return () => listeners.delete(listener);
}
