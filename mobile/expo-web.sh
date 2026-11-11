#!/bin/bash
# Wrapper script to run Expo web with proper environment variables and permissions

# Set up temporary Expo directory with full permissions
export CI=1
export __UNSAFE_EXPO_HOME_DIRECTORY=/tmp/expo_web_$$

# Create directory with proper permissions
mkdir -p "$__UNSAFE_EXPO_HOME_DIRECTORY"
chmod 755 "$__UNSAFE_EXPO_HOME_DIRECTORY"

# Run Expo web
echo "Starting Expo Web with temporary home at: $__UNSAFE_EXPO_HOME_DIRECTORY"
npx expo start --web --port 8082

# Cleanup on exit
trap "rm -rf '$__UNSAFE_EXPO_HOME_DIRECTORY'" EXIT
