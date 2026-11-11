import apiClient from './apiClient';

export type ParishNotification = {
    id: number;
    kind: 'mass_request_status';
    title: string;
    message: string;
    mass_request_id: number | null;
    created_at: string;
};

export async function fetchParishNotifications() {
    const response = await apiClient.get<ParishNotification[]>('/notifications/');
    return response.data;
}

export async function markParishNotificationRead(id: number) {
    await apiClient.post(`/notifications/${id}/read/`);
}

export async function markAllParishNotificationsRead() {
    await apiClient.post('/notifications/read/');
}
