import apiClient from './apiClient';

export async function fetchGroups() {
    const response = await apiClient.get('/groupes/');
    return response.data;
}
