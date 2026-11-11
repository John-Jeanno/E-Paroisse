import { StatusBar } from 'expo-status-bar';
import { NavigationContainer } from '@react-navigation/native';
import React from 'react';
import { Platform } from 'react-native';
import * as SplashScreen from 'expo-splash-screen';
import AppNavigator from './src/navigation/AppNavigator';
import LiturgicalThemeProvider from './src/theme/LiturgicalTheme';
import { OfflineProvider } from './src/components/OfflineProvider';
import OfflineNotice from './src/components/OfflineNotice';

void SplashScreen.preventAutoHideAsync().catch(() => undefined);

export default function App() {
    React.useEffect(() => {
        const hideSplash = async () => {
            try {
                await SplashScreen.hideAsync();
            } catch { }
        };

        hideSplash();
        if (Platform.OS === 'web' && 'serviceWorker' in navigator) {
            void navigator.serviceWorker.register('/service-worker.js').catch((error: unknown) => {
                console.warn('Le mode hors ligne de la PWA n’a pas pu être activé.', error);
            });
        }
    }, []);

    return (
        <LiturgicalThemeProvider>
            <OfflineProvider>
                <OfflineNotice />
                <NavigationContainer>
                    <AppNavigator />
                    <StatusBar style="auto" />
                </NavigationContainer>
            </OfflineProvider>
        </LiturgicalThemeProvider>
    );
}
