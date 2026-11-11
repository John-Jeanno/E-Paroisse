import { useWindowDimensions } from 'react-native';

export default function useResponsiveLayout() {
    const { width } = useWindowDimensions();
    const isDesktop = width >= 1024;
    const isTablet = width >= 700 && width < 1024;

    return {
        width,
        isDesktop,
        isTablet,
        contentMaxWidth: isDesktop ? 1320 : isTablet ? 960 : width,
        formMaxWidth: isDesktop ? 640 : isTablet ? 720 : width,
        horizontalPadding: width >= 1200 ? 40 : width >= 700 ? 32 : 20,
    };
}
