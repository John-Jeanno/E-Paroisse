import React from 'react';
import { Image } from 'react-native';

type Props = {
    size?: number;
};

export default function ParishMaryLogo({ size = 40 }: Props) {
    return (
        <Image
            source={require('../../assets/parish-logo-white.png')}
            resizeMode="contain"
            accessible
            accessibilityLabel="Vierge Marie, Notre Dame des Anges"
            style={{ width: size, height: size }}
        />
    );
}
