#!/bin/bash
# Wrapper script to run iOS build with proper environment and cleanup

cd "$(dirname "$0")" || exit 1

echo "🔧 Preparing iOS build environment..."

# Clean CocoaPods caches
echo "Cleaning CocoaPods..."
rm -f ios/Podfile.lock
rm -rf ios/Pods
rm -rf ~/Library/Developer/Xcode/DerivedData/*EParoisse* 2>/dev/null || true

# Set up Expo environment
export CI=1
export __UNSAFE_EXPO_HOME_DIRECTORY=/tmp/expo_ios_$$

mkdir -p "$__UNSAFE_EXPO_HOME_DIRECTORY"
chmod 755 "$__UNSAFE_EXPO_HOME_DIRECTORY"

echo "Starting iOS build..."
echo "⚠️  Note: Using JSC engine instead of Hermes to avoid network issues"

# Run iOS build directly via Expo CLI
npx expo run:ios

# Cleanup on exit
trap "rm -rf '$__UNSAFE_EXPO_HOME_DIRECTORY'" EXIT
