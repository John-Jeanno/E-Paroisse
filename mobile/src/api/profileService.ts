import apiClient from './apiClient';

export async function fetchProfile() {
    const response = await apiClient.get('/auth/profile/');
    return response.data;
}

export async function updateProfile(profileData: {
    first_name?: string;
    last_name?: string;
    group_name?: string;
    parish_entity_names?: string[];
}) {
    const response = await apiClient.put('/auth/profile/', profileData);
    return response.data;
}
