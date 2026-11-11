import apiClient from './apiClient';
import type { Announcement } from '../types/Announcement';

export type GlobalSearchResult = {
    kind: 'announcement' | 'reading' | 'question' | 'parishioner';
    id: string;
    profile_id?: number;
    title: string;
    subtitle: string;
    announcement?: Announcement;
};

export async function searchParishContent(query: string) {
    const response = await apiClient.get<GlobalSearchResult[]>('/recherche/', {
        params: { q: query },
    });
    return response.data;
}
