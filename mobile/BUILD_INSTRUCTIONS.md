# Instructions de Build - E-Paroisse Mobile

## ✅ Disponible

Le client natif Android/iOS, le site Web et la PWA utilisent le même code
Expo. Une publication Web/PWA met à jour le site, mais ne remplace pas une
application native déjà installée : celle-ci doit être reconstruite puis
redistribuée. La production Docker reconstruit le bundle Web/PWA et l'API
applique ses migrations au démarrage.

### 1. **Metro Bundler (Développement)**

```bash
npm start
# Démarre Metro pour Expo Go ou un client natif
npm start -- --lan
# Garder le terminal ouvert pendant le test
```

### 2. **Build Web**

```bash
npm run web
# Publie l’URL Expo sur le réseau local (port 8083)
# Le téléphone et l’ordinateur doivent être sur le même Wi-Fi
# Utilise react-dom et react-native-web
```

Dans VS Code, lancez d’abord la tâche **E-Paroisse API Django**, puis
**E-Paroisse Web (réseau local)** via **Terminal → Exécuter la tâche**.
Les deux tâches affichent leurs logs dans le terminal intégré.

Sur l’iPhone, ouvrez l’URL affichée par Expo dans Safari, puis choisissez
**Partager → Sur l’écran d’accueil**. L’application utilise un manifeste et
une icône dédiés. En mode réseau local, le Mac et l’iPhone doivent rester sur
le même Wi-Fi et les deux serveurs (web et API) doivent rester lancés.

### Accès depuis un autre réseau Wi-Fi (privé avec Tailscale)

Pour accéder à l'application depuis l'iPhone sans partager le Wi-Fi du Mac,
utilisez Tailscale Serve, qui rend le site disponible en HTTPS uniquement aux
appareils connectés à votre réseau privé Tailscale :

1. Installez [Tailscale sur le Mac](https://tailscale.com/download/mac) et
   [Tailscale sur l'iPhone](https://apps.apple.com/app/tailscale/id1470499037),
   puis connectez les deux au même compte Tailscale. Sur l'iPhone, laissez
   Tailscale connecté.
2. Le Mac doit rester allumé, connecté à Internet et connecté à Tailscale.
   Dans VS Code, démarrez **E-Paroisse API Django**, puis
   **E-Paroisse Web (réseau local)**.
3. Lancez la tâche VS Code **E-Paroisse Accès privé (Tailscale)**. Elle publie
   le site à la racine HTTPS et l'API sous `/api` et affiche l'adresse `https://…ts.net`.
   La première utilisation peut vous demander d'autoriser HTTPS pour votre
   réseau Tailscale.
4. Sur l'iPhone (même en 4G/5G ou sur un autre Wi-Fi), ouvrez cette adresse
   dans Safari et choisissez **Partager → Sur l'écran d'accueil**.

Cette méthode n'ouvre pas le site à tout Internet : seuls les appareils
autorisés sur votre réseau Tailscale peuvent le joindre. Ne remplacez pas
`tailscale serve` par `tailscale funnel`, qui rendrait le service public.
L'application et Django tournent toujours sur le Mac ; si le Mac ou l'un des
serveurs s'arrête, l'application ne sera plus accessible. Pour une application
toujours en ligne, il faudra un hébergement public de production avec base de
données persistante. Consultez la [documentation Tailscale Serve](https://tailscale.com/docs/features/tailscale-serve).

### Numéro de paiement pour une demande de messe

Le numéro de réception des montants est affiché dans le formulaire « Demande
de messe » avec le message **« Envoyer sur ce numéro le montant »**. Pour
configurer le vrai numéro, définissez `MASS_REQUEST_PAYMENT_PHONE` dans
l'environnement du serveur Django, par exemple dans `backend/.env` :

```dotenv
MASS_REQUEST_PAYMENT_PHONE=+221XXXXXXXXX
```

Remplacez la valeur d'exemple par le numéro réel du bénéficiaire, puis
redémarrez la tâche **E-Paroisse API Django**. Le numéro est servi par
`/api/demandes-messe/paiement/`; s'il n'est pas défini, l'application indique
explicitement que le numéro doit encore être configuré. Cette fonctionnalité
affiche les coordonnées de paiement mais n'effectue pas elle-même de transfert.

Cette URL locale n’est pas accessible depuis Internet et peut changer si
l’adresse du Mac change. Pour un accès Internet, déployez le site et l’API sur
un hébergement public HTTPS, puis définissez `EXPO_PUBLIC_API_URL` comme URL
complète de l’API (par exemple `https://api.exemple.org/api`) et
`DJANGO_CORS_ALLOWED_ORIGINS` comme origine exacte du site (par exemple
`https://paroisse.exemple.org`). Ne rendez pas le serveur de développement
Django accessible publiquement.

### 3. **Build Web (clean)**

```bash
npm run web-clean
# Nettoie le cache Expo et relance le serveur
```

---

## ⚠️ Limitations Actuelles

### Test sur iPhone avec Expo Go

Le projet utilise Expo SDK 57, compatible avec la version actuelle d'Expo Go.

```bash
npm start -- --lan
# Scanner le QR code affiché dans le terminal avec l'app Appareil photo de l'iPhone
```

Le Mac et l'iPhone doivent être sur le même réseau Wi-Fi. Un build natif iOS
direct nécessite un profil de signature Xcode valide.

### Android Build

Le plugin Gradle React Native requiert JDK 17. JDK 25 n’est pas compatible et
peut échouer pendant le chargement du plugin `com.facebook.react.settings`.
Sur ce Mac, Temurin 17 est installé dans la bibliothèque utilisateur :

```bash
export JAVA_HOME="$HOME/Library/Java/JavaVirtualMachines/temurin-17.jdk/Contents/Home"
export PATH="$JAVA_HOME/bin:$PATH"
java -version
cd android
./gradlew -PreactNativeArchitectures=arm64-v8a assembleDebug
```

Cette commande produit un APK pour les téléphones Android ARM64. Pour inclure
les architectures d’émulateur et les appareils Android 32 bits, retirez
`-PreactNativeArchitectures=arm64-v8a`. Le SDK Android doit également être
installé et configuré pour produire un APK.
Pour une installation sur iPhone, un build signé avec le profil de signature
Xcode de l’équipe est requis.

### iOS Build

Installer les pods depuis le dossier `ios`, puis construire le workspace CocoaPods
(et non le projet Xcode seul) :

```bash
cd ios
pod install
xcodebuild -workspace EParoisse.xcworkspace -scheme EParoisse \
  -sdk iphonesimulator -configuration Debug CODE_SIGNING_ALLOWED=NO build
```

Le déploiement VPS met à jour le site et la PWA, mais ne distribue pas de build
natif aux appareils.

---

## Scripts Disponibles

| Commande | Description |
| ---------- | ------------- |
| `npm start` | Démarre Metro Bundler |
| `npm run web` | Démarre serveur web Expo |
| `npm run web-clean` | Nettoie cache Expo + web |
| `npm run ios-direct` | Test iOS build (nécessite réseau) |
| `npx expo install --check` | Vérifie l’alignement des modules natifs Expo |
| `npm run simulate` | Exécute le simulateur Python |

---

## 📝 Configuration

### Dépendances Installées ✅
- Expo SDK 57 (`expo@~57.0.32`)
- React and React Native versions aligned with SDK 57 via `npx expo install --fix`
- `expo-constants` déclaré directement pour les imports de l’application
- react-dom@19.2.3 (web)
- react-native-web@^0.21.0 (web)

Expo Go for iOS only supports the current SDK. To start the mobile app on a
phone connected to the same Wi-Fi network, run `npx expo start --lan` and scan
the QR code with the iPhone camera. Keep the terminal running while testing.

SDK 55 and later require the New Architecture. The iOS native project enables
it in `ios/Podfile.properties.json`; Android already enables it in
`android/gradle.properties`.

### Podfile iOS

- Hermes activé pour rester cohérent avec Expo SDK 57
- iOS 16.4+ requis
- Flipper disabled (obsolète)
- Les modules React Native et Expo sont autolinkés par CocoaPods (`use_native_modules!` et `use_expo_modules!`).

---

## 🔧 Troubleshooting

### Erreur "Port 8081 already in use"

```bash
# Nettoyer les processus Expo stale
pkill -f 'expo start'
pkill -f 'npx expo'
rm -rf /tmp/expo*
```

### Erreur permissions ".expo"

Les scripts utilisent des répertoires temporaires (/tmp) pour éviter les problèmes de permissions.
Automatiquement géré par les wrappers.

---

## 📦 Pour les builds production

Une fois les restrictions de sandbox levées :

### iOS

```bash
npm run ios-direct
```

### Android  

```bash
# Après configuration d'Android SDK
npm run android
```

---

**État du projet** : ✅ Prêt pour développement local avec Metro + Web
