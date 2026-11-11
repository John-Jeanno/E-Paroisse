import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { AppState } from 'react-native';

// --- 1. Theme Definition and Color Palette ---

type LiturgicalSeason =
    | 'ordinary'
    | 'advent'
    | 'advent-gaudete'
    | 'christmas'
    | 'lent'
    | 'lent-laetare'
    | 'holyweek'
    | 'easter'
    | 'pentecost';

type Theme = {
    season: LiturgicalSeason;
    seasonLabel: string;
    seasonDescription: string;
    primary: string;
    background: string;
    text: string;
    card: string;
    accent: string;
};

const themes: Record<LiturgicalSeason, Omit<Theme, 'season'>> = {
    ordinary: {
        seasonLabel: 'Temps ordinaire',
        seasonDescription: 'Un temps de croissance spirituelle et de vie quotidienne.',
        primary: '#3F7048',
        background: '#F1F3EC',
        text: '#302F2B',
        card: '#FFFEFA',
        accent: '#C4D5C3',
    },
    advent: {
        seasonLabel: 'Avent',
        seasonDescription: 'Période de préparation à la venue du Christ.',
        primary: '#5E4778',
        background: '#F3EFF7',
        text: '#332D38',
        card: '#FFFCFF',
        accent: '#D4C5E1',
    },
    'advent-gaudete': {
        seasonLabel: 'Gaudete',
        seasonDescription: 'Dimanche de la joie, au cœur de l’Avent.',
        primary: '#A84E70',
        background: '#FBF0F4',
        text: '#382B30',
        card: '#FFFCFD',
        accent: '#E9BDCE',
    },
    christmas: {
        seasonLabel: 'Noël',
        seasonDescription: 'Célébration de la naissance du Christ et de la lumière.',
        primary: '#805E12',
        background: '#FBF7E9',
        text: '#342F23',
        card: '#FFFEFA',
        accent: '#E6D7A5',
    },
    lent: {
        seasonLabel: 'Carême',
        seasonDescription: 'Temps de conversion, de prière et de partage.',
        primary: '#684778',
        background: '#F4EFF6',
        text: '#322C36',
        card: '#FFFCFF',
        accent: '#D0BFDE',
    },
    'lent-laetare': {
        seasonLabel: 'Laetare',
        seasonDescription: 'Dimanche de la joie, une pause au milieu du Carême.',
        primary: '#A84E70',
        background: '#FBF0F4',
        text: '#382B30',
        card: '#FFFCFD',
        accent: '#E9BDCE',
    },
    holyweek: {
        seasonLabel: 'Semaine Sainte',
        seasonDescription: 'Semaine de la Passion, de la Croix et de la Résurrection.',
        primary: '#913C43',
        background: '#F8EEEE',
        text: '#352A2A',
        card: '#FFFCFC',
        accent: '#E2BFC1',
    },
    easter: {
        seasonLabel: 'Pâques',
        seasonDescription: 'Temps de la Résurrection et de la joie de vivre en Christ.',
        primary: '#805E12',
        background: '#FBF7E9',
        text: '#342F23',
        card: '#FFFEFA',
        accent: '#E6D7A5',
    },
    pentecost: {
        seasonLabel: 'Pentecôte',
        seasonDescription: 'Fête de l’Esprit Saint et de l’envoi missionnaire.',
        primary: '#963C3D',
        background: '#F8EEEE',
        text: '#352A2A',
        card: '#FFFCFC',
        accent: '#E2BFC1',
    },
};

const defaultTheme: Theme = {
    ...themes.ordinary,
    season: 'ordinary',
};

// --- 2. Liturgical Date Calculation Logic ---

namespace LiturgicalDateUtils {
    export function easterDate(year: number): Date {
        const a = year % 19;
        const b = Math.floor(year / 100);
        const c = year % 100;
        const d = Math.floor(b / 4);
        const e = b % 4;
        const f = Math.floor((b + 8) / 25);
        const g = Math.floor((b - f + 1) / 3);
        const h = (19 * a + b - d - g + 15) % 30;
        const i = Math.floor(c / 4);
        const k = c % 4;
        const l = (32 + 2 * e + 2 * i - h - k) % 7;
        const m = Math.floor((a + 11 * h + 22 * l) / 451);
        const month = Math.floor((h + l - 7 * m + 114) / 31);
        const day = ((h + l - 7 * m + 114) % 31) + 1;
        return new Date(year, month - 1, day);
    }

    export function addDays(d: Date, n: number): Date {
        const dd = new Date(d);
        dd.setDate(dd.getDate() + n);
        return dd;
    }

    export function isSameDay(a: Date, b: Date): boolean {
        return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
    }

    function findSundayBetween(year: number, month: number, startDay: number, endDay: number): Date | null {
        for (let d = startDay; d <= endDay; d++) {
            const dt = new Date(year, month - 1, d);
            if (dt.getDay() === 0) return dt; // Sunday
        }
        return null;
    }

    export function getLiturgicalSeason(date: Date): LiturgicalSeason {
        const y = date.getFullYear();
        const today = new Date(y, date.getMonth(), date.getDate());

        const easter = easterDate(y);
        const ashWednesday = addDays(easter, -46);
        const palmSunday = addDays(easter, -7);
        const pentecost = addDays(easter, 49);
        const easterSeasonEnd = pentecost;

        const adventStart = findSundayBetween(y, 11, 27, 30) || findSundayBetween(y, 12, 1, 3);
        const adventEnd = new Date(y, 11, 24);

        if (adventStart && today >= adventStart && today <= adventEnd) {
            const gaudete = addDays(adventStart, 14);
            if (isSameDay(today, gaudete)) return 'advent-gaudete';
            return 'advent';
        }

        if ((today.getMonth() === 11 && today.getDate() >= 25) ||
            (today.getMonth() === 0 && today.getDate() <= 13)) {
            return 'christmas';
        }

        if (today >= ashWednesday && today < palmSunday) {
            const firstSundayOfLent = addDays(ashWednesday, 7 - ashWednesday.getDay());
            const laetare = addDays(firstSundayOfLent, 21);
            if (isSameDay(today, laetare)) return 'lent-laetare';
            return 'lent';
        }

        if (today >= palmSunday && today < easter) {
            return 'holyweek';
        }

        if (today >= easter && today <= easterSeasonEnd) {
            if (isSameDay(today, pentecost)) return 'pentecost';
            return 'easter';
        }

        return 'ordinary';
    }
}

// --- 3. Theme Provider and Context ---

const ThemeContext = createContext<Theme>(defaultTheme);

export function useTheme(): Theme {
    return useContext(ThemeContext);
}

export const LiturgicalThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [theme, setTheme] = useState<Theme>(defaultTheme);

    useEffect(() => {
        let midnightTimer: ReturnType<typeof setTimeout>;

        const updateTheme = () => {
            const now = new Date();
            const season = LiturgicalDateUtils.getLiturgicalSeason(now);
            setTheme({ ...themes[season], season });
            const tomorrow = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1);
            midnightTimer = setTimeout(updateTheme, tomorrow.getTime() - now.getTime() + 1000);
        };

        const refreshWhenActive = AppState.addEventListener('change', (state) => {
            if (state === 'active') {
                clearTimeout(midnightTimer);
                updateTheme();
            }
        });

        updateTheme();
        return () => {
            clearTimeout(midnightTimer);
            refreshWhenActive.remove();
        };
    }, []);

    const value = useMemo(() => theme, [theme]);

    return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
};

export default LiturgicalThemeProvider;
