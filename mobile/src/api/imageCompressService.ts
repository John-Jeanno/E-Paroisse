import * as ImageManipulator from 'expo-image-manipulator';

export async function compressImage(uri: string): Promise<string> {
    const result = await ImageManipulator.manipulateAsync(uri, [], {
        compress: 0.6,
        format: ImageManipulator.SaveFormat.JPEG,
    });
    return result.uri;
}
