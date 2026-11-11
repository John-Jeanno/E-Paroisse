import apiClient from './apiClient';

export type MassSchedule = {
    id: number;
    weekday: number | null;
    weekday_label: string | null;
    date: string | null;
    time: string;
    location: string;
};

export type DonationSettings = {
    wave_identifier: string;
    orange_money_identifier: string;
    instructions: string;
};

export async function fetchMassSchedules() {
    const response = await apiClient.get<MassSchedule[]>('/horaires-messes/');
    return response.data;
}

export async function fetchDonationSettings() {
    const response = await apiClient.get<DonationSettings>('/dons/');
    return response.data;
}
