import apiClient from './apiClient';
import { sendOrQueue } from './offlineService';

export type MassRequestPaymentInfo = {
    payment_phone: string;
    contact_phone: string;
};

type MassRequestResponse = {
    blocked?: boolean;
    detail?: string;
    status?: string;
    phone?: string;
    locality?: string;
    contact_email?: string;
    preferred_date?: string;
    message: string;
};

export async function createMassRequest(data: { phone: string; contact_email?: string; locality: string; preferred_date?: string; message: string }) {
    return sendOrQueue<MassRequestResponse>(
        { method: 'post', url: '/demandes-messe/', data },
        () => ({ ...data, status: 'pending_sync' }),
    );
}

export async function fetchMassRequestPaymentInfo(): Promise<MassRequestPaymentInfo> {
    const res = await apiClient.get('/demandes-messe/paiement/');
    return res.data;
}

export async function fetchMassRequests() {
    const res = await apiClient.get('/demandes-messe/');
    return res.data;
}

export default { createMassRequest };
