import apiClient from './apiClient';

export async function uploadImage(fileUri: string): Promise<string> {
    const formData = new FormData();
    // Extract filename
    const name = fileUri.split('/').pop() || 'upload.jpg';
    // Infer type
    const type = 'image/jpeg';

    // @ts-ignore - FormData file object for React Native
    formData.append('image', { uri: fileUri, name, type });

    const res = await apiClient.post('/upload-image/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
    });

    return res.data.url;
}

export default { uploadImage };
