import React, { useState } from 'react';
import { Button, Image, StyleSheet, Text, View } from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import { compressImage } from '../api/imageCompressService';
import { uploadImage } from '../api/uploadService';
import { useTheme } from '../theme/LiturgicalTheme';
import useResponsiveLayout from '../hooks/useResponsiveLayout';

export default function ImageUploadScreen() {
    const theme = useTheme();
    const { formMaxWidth, horizontalPadding } = useResponsiveLayout();
    const [originalUri, setOriginalUri] = useState<string | null>(null);
    const [compressedUri, setCompressedUri] = useState<string | null>(null);
    const [message, setMessage] = useState('');

    const pickImage = async () => {
        const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
        if (!permission.granted) {
            setMessage('Autorisation d’accès aux images refusée.');
            return;
        }

        const result = await ImagePicker.launchImageLibraryAsync({
            mediaTypes: ImagePicker.MediaTypeOptions.Images,
            allowsEditing: false,
            quality: 1,
        });

        if (!result.canceled) {
            const imageUri = result.assets?.[0]?.uri;
            if (!imageUri) {
                setMessage('Impossible de récupérer l’image sélectionnée.');
                return;
            }

            setOriginalUri(imageUri);
            setMessage('Compression en cours...');
            const compressed = await compressImage(imageUri);
            setCompressedUri(compressed);
            setMessage('Image compressée avec succès. Upload en cours...');
            try {
                const url = await uploadImage(compressed);
                setMessage(`Image uploadée: ${url}`);
            } catch (err) {
                setMessage('Échec de l’upload.');
            }
        }
    };

    return (
        <View style={[styles.container, { backgroundColor: theme.background, maxWidth: formMaxWidth, paddingHorizontal: horizontalPadding }]}>
            <Text style={[styles.title, { color: theme.primary }]}>Compression d'image</Text>
            <Button title="Choisir une image" color={theme.primary} onPress={pickImage} />
            {message ? <Text style={[styles.message, { color: theme.text }]}>{message}</Text> : null}
            {originalUri ? (
                <View style={styles.preview}>
                    <Text style={styles.previewLabel}>Original</Text>
                    <Image source={{ uri: originalUri }} style={styles.image} />
                </View>
            ) : null}
            {compressedUri ? (
                <View style={styles.preview}>
                    <Text style={styles.previewLabel}>Compressée</Text>
                    <Image source={{ uri: compressedUri }} style={styles.image} />
                </View>
            ) : null}
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        width: '100%',
        alignSelf: 'center',
        padding: 24,
        backgroundColor: '#fff',
    },
    title: {
        fontSize: 22,
        fontWeight: 'bold',
        marginBottom: 16,
    },
    message: {
        marginVertical: 12,
        color: '#333',
    },
    preview: {
        marginTop: 16,
    },
    previewLabel: {
        marginBottom: 8,
        fontWeight: '600',
    },
    image: {
        width: '100%',
        height: 200,
        borderRadius: 10,
    },
});
