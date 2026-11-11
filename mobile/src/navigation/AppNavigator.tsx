import React from 'react';
import { AppState, Pressable, Text, View, useWindowDimensions } from 'react-native';
import { useTheme } from '../theme/LiturgicalTheme';
import ParishMaryLogo from '../components/ParishMaryLogo';
import AnnouncementNotificationBell from '../components/AnnouncementNotificationBell';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import Svg, { Path } from 'react-native-svg';
import { useCallback, useState } from 'react';
import { useFocusEffect } from '@react-navigation/native';
import { getToken } from '../api/tokenStorage';
import { fetchMessagingUnreadSummary } from '../api/messagingService';
import AuthScreen from '../screens/AuthScreen';
import OnboardingScreen from '../screens/OnboardingScreen';
import HomeScreen from '../screens/HomeScreen';
import AnnouncementsScreen from '../screens/AnnouncementsScreen';
import AnnouncementDetailScreen from '../screens/AnnouncementDetailScreen';
import LiturgieScreen from '../screens/LiturgieScreen';
import ProfileScreen from '../screens/ProfileScreen';
import ImageUploadScreen from '../screens/ImageUploadScreen';
import RequestMassScreen from '../screens/RequestMassScreen';
import LiturgicalCalendarScreen from '../screens/LiturgicalCalendarScreen';
import MassRequestsScreen from '../screens/MassRequestsScreen';
import MessagingScreen from '../screens/MessagingScreen';
import CatecheseScreen from '../screens/CatecheseScreen';
import SpiritualGameScreen from '../screens/SpiritualGameScreen';
import SearchScreen from '../screens/SearchScreen';
import MassScheduleScreen from '../screens/MassScheduleScreen';
import DonationsScreen from '../screens/DonationsScreen';

export type RootStackParamList = {
    Auth: undefined;
    Onboarding: undefined;
    Home: undefined;
    Annonces: undefined;
    AnnouncementDetail: { announcement: import('../types/Announcement').Announcement };
    Search: { query?: string } | undefined;
    RequestMass: undefined;
    Liturgie: undefined;
    Profil: undefined;
    ImageUpload: undefined;
    LiturgicalCalendar: undefined;
    MassRequests: undefined;
    MassSchedule: undefined;
    Donations: undefined;
    Messaging: { contactId?: number; entityId?: number } | undefined;
    Catechese: { lessonId?: string } | undefined;
    SpiritualGame: { challengeId?: number } | undefined;
};

const Stack = createNativeStackNavigator<RootStackParamList>();

function HeaderActions({ compactHeader }: { compactHeader: boolean }) {
    const navigation = useNavigation<NativeStackNavigationProp<RootStackParamList>>();
    const [unreadCount, setUnreadCount] = useState(0);
    const [error, setError] = useState('');
    const [unreadSummary, setUnreadSummary] = useState<Awaited<ReturnType<typeof fetchMessagingUnreadSummary>> | null>(null);

    useFocusEffect(useCallback(() => {
        let active = true;
        const updateUnreadCount = async () => {
            try {
                const token = await getToken();
                if (!active) return;
                if (!token) {
                    setUnreadCount(0);
                    setUnreadSummary(null);
                    setError('');
                    return;
                }
                const summary = await fetchMessagingUnreadSummary();
                if (active) {
                    setUnreadCount(summary.total_count);
                    setUnreadSummary(summary);
                    setError('');
                }
            } catch {
                if (active) setError('Le nombre de messages non lus ne peut pas être actualisé.');
            }
        };

        void updateUnreadCount();
        const interval = setInterval(() => {
            if (AppState.currentState === 'active') void updateUnreadCount();
        }, 15000);
        const subscription = AppState.addEventListener('change', (state) => {
            if (state === 'active') void updateUnreadCount();
        });
        return () => {
            active = false;
            clearInterval(interval);
            subscription.remove();
        };
    }, []));

    return (
        <View style={{ flexDirection: 'row', alignItems: 'center' }}>
            <Pressable
                accessibilityRole="button"
                accessibilityLabel={`Ouvrir la messagerie${unreadCount ? `, ${unreadCount} message(s) non lu(s)` : ''}`}
                accessibilityHint={error || undefined}
                hitSlop={6}
                onPress={() => {
                    const unreadConversation = unreadSummary?.unread_private_conversations[0];
                    const unreadEntity = unreadSummary?.unread_entities[0];
                    if (unreadConversation) {
                        navigation.navigate('Messaging', { contactId: unreadConversation.profile_id });
                    } else if (unreadEntity) {
                        navigation.navigate('Messaging', { entityId: unreadEntity.entity_id });
                    } else {
                        navigation.navigate('Messaging');
                    }
                }}
                style={{
                    width: compactHeader ? 38 : 44,
                    height: 44,
                    alignItems: 'center',
                    justifyContent: 'center',
                }}
            >
                <Svg width={compactHeader ? 22 : 25} height={compactHeader ? 22 : 25} viewBox="0 0 24 24" fill="none">
                    <Path
                        d="M4 5.5h16v11H9l-5 3v-14Z"
                        stroke="#fff"
                        strokeWidth={1.8}
                        strokeLinejoin="round"
                    />
                    <Path d="M8 9h8M8 13h5" stroke="#fff" strokeWidth={1.8} strokeLinecap="round" />
                </Svg>
                {unreadCount > 0 ? (
                    <View style={{
                        position: 'absolute',
                        top: 2,
                        right: 2,
                        minWidth: 18,
                        height: 18,
                        paddingHorizontal: 4,
                        borderRadius: 9,
                        backgroundColor: '#d62828',
                        alignItems: 'center',
                        justifyContent: 'center',
                    }}>
                        <Text style={{ color: '#fff', fontSize: 10, fontWeight: '700' }}>
                            {unreadCount > 99 ? '99+' : unreadCount}
                        </Text>
                    </View>
                ) : null}
            </Pressable>
            <AnnouncementNotificationBell compact={compactHeader} />
        </View>
    );
}

export default function AppNavigator() {
    const theme = useTheme();
    const { width } = useWindowDimensions();
    const compactHeader = width < 400;

    const hexToRgb = (hex: string) => {
        const clean = hex.replace('#', '');
        const bigint = parseInt(clean, 16);
        return [(bigint >> 16) & 255, (bigint >> 8) & 255, bigint & 255];
    };

    const luminance = (hex: string) => {
        try {
            const [r, g, b] = hexToRgb(hex);
            const a = [r, g, b].map((v) => {
                v /= 255;
                return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
            });
            return 0.2126 * a[0] + 0.7152 * a[1] + 0.0722 * a[2];
        } catch {
            return 0;
        }
    };

    const headerTintColor = luminance(theme.primary) > 0.179 ? '#211a16' : '#fff';

    return (
        <Stack.Navigator
            initialRouteName="Auth"
            screenOptions={{
                headerShown: true,
                headerStyle: { backgroundColor: theme.primary },
                headerTintColor,
                contentStyle: { backgroundColor: theme.background },
                headerRight: () => <HeaderActions compactHeader={compactHeader} />,
                headerTitleAlign: 'left',
                headerTitle: () => (
                    <View style={{
                        flexDirection: 'row',
                        alignItems: 'center',
                        gap: compactHeader ? 5 : 9,
                        maxWidth: Math.max(100, width - (compactHeader ? 160 : 225)),
                        flexShrink: 1,
                    }}>
                        <ParishMaryLogo size={compactHeader ? 26 : 38} />
                        <Text
                            numberOfLines={1}
                            adjustsFontSizeToFit
                            minimumFontScale={compactHeader ? 0.6 : 0.8}
                            style={{
                                color: headerTintColor,
                                fontSize: compactHeader ? 13 : 16,
                                fontWeight: '700',
                                lineHeight: 20,
                                flexShrink: 1,
                            }}
                        >
                            Paroisse NDA
                        </Text>
                    </View>
                ),
            }}
        >
            <Stack.Screen name="Auth" component={AuthScreen} options={{ title: 'Connexion', headerRight: () => null }} />
            <Stack.Screen name="Onboarding" component={OnboardingScreen} options={{ title: 'Bienvenue', headerRight: () => null }} />
            <Stack.Screen name="Home" component={HomeScreen} options={{ title: 'Accueil' }} />
            <Stack.Screen name="Search" component={SearchScreen} options={{ title: 'Recherche' }} />
            <Stack.Screen name="RequestMass" component={RequestMassScreen} options={{ title: 'Demander une messe' }} />
            <Stack.Screen name="Annonces" component={AnnouncementsScreen} options={{ title: 'Annonces' }} />
            <Stack.Screen name="AnnouncementDetail" component={AnnouncementDetailScreen} options={{ title: 'Publication' }} />
            <Stack.Screen name="Liturgie" component={LiturgieScreen} options={{ title: 'Liturgie' }} />
            <Stack.Screen name="Profil" component={ProfileScreen} options={{ title: 'Profil' }} />
            <Stack.Screen name="ImageUpload" component={ImageUploadScreen} options={{ title: 'Compression d\'image' }} />
            <Stack.Screen name="LiturgicalCalendar" component={LiturgicalCalendarScreen} options={{ title: 'Calendrier liturgique' }} />
            <Stack.Screen name="MassRequests" component={MassRequestsScreen} options={{ title: 'Mes demandes' }} />
            <Stack.Screen name="MassSchedule" component={MassScheduleScreen} options={{ title: 'Heures de messes' }} />
            <Stack.Screen name="Donations" component={DonationsScreen} options={{ title: 'Dons' }} />
            <Stack.Screen name="Messaging" component={MessagingScreen} options={{ title: 'Messagerie' }} />
            <Stack.Screen name="Catechese" component={CatecheseScreen} options={{ title: 'Catéchèse' }} />
            <Stack.Screen name="SpiritualGame" component={SpiritualGameScreen} options={{ title: 'Jeux spirituels' }} />
        </Stack.Navigator>
    );
}
