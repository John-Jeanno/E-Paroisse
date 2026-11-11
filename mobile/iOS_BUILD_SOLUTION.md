# 📱 Solution iOS Build - Sandbox Issue

## ❌ Problème : Hermes Engine 403 Forbidden

L'erreur `[!] Failed to load 'hermes-engine' podspec: 403 "Forbidden"` est causée par le **sandbox réseau de VS Code Insiders** qui bloque :

- Maven Central (pour Hermes binaries)
- npm registry (pour JSC alternative)

## 🎯 Deux Solutions

### **Solution 1 : Utiliser Expo Go (Facile, Immédiat) ✅**

**L'application fonctionne déjà !**

```bash
npm start                    # Lance Metro sur port 8081
# Installer Expo Go sur iPhone/Android
# Scanner le QR code affiché dans le terminal
# Tester directement sur votre téléphone
```

**Avantages** :

- ✅ Fonctionne maintenant
- ✅ Aucune compilation native requise
- ✅ Hot reload en temps réel
- ✅ Parfait pour développement
- ✅ Tester sur votre téléphone réel

**Limitations** :

- ⚠️ Pas de build APK/IPA final
- ⚠️ Require Expo Go app

---

### **Solution 2 : Lever le Sandbox VS Code (Complexe, Permanent) 🔓**

Si vous avez **besoin** de compiler les binaires iOS/Android natifs :

#### Option A : Utiliser Terminal Normal (macOS)

1. Ouvrir Terminal normal (pas VS Code)

2. ```bash
   cd /Users/mac/E-paroisse/mobile
   npm run ios-direct    # Compile vers iOS
   ```

3. Terminal normal n'a pas de sandbox réseau

#### Option B : Demander à VS Code de Lever le Sandbox

VS Code devrait afficher une notification pour accorder l'accès réseau. Si vous ne la voyez pas :

1. Ouvrir **Terminal** dans VS Code
2. Exécuter : `npm run ios-direct`
3. **Accepter la notification de sandbox** quand elle apparaît

#### Option C : Configurer VS Code pour Désactiver le Sandbox

1. Ouvrir `settings.json` de VS Code
2. Chercher `terminal.integrated`
3. Ajouter (VS Code Insiders) :

   ```json
   "terminal.integratedUnsandboxed": true
   ```

4. Redémarrer VS Code

---

## 📋 Checklist : Quand Choisir Quoi?

| Cas d'Usage | Solution Recommandée |
| --- | --- |
| Développement rapide / Tests | Expo Go ✅ |
| Build iOS/Android final (.ipa/.apk) | Terminal Normal ou Lever Sandbox |
| Tester sur téléphone réel | Expo Go ✅ |
| Publication App Store | Terminal Normal ou Lever Sandbox |

---

## 🚀 Commandes Utiles

```bash
# Expo Go (Fonctionne maintenant)
npm start               # Metro Bundler + QR code
npm run web            # Web preview

# iOS Native (Nécessite sandbox levé)
npm run ios-direct     # Compile vers iPhone simulator
npm run ios            # Compile avec wrapper script

# Nettoyage complet
npm run web-clean      # Clean cache web
rm -rf ios/Pods        # Clean iOS pods
rm -rf node_modules    # Rebuild everything (long)
```

---

## 🧪 Vérifier le Sandbox

```bash
# Terminal VS Code (bloqué)
curl https://registry.npmjs.org/react-native
# Résultat : 403 Forbidden ❌

# Terminal Normal (devrait fonctionner)
curl https://registry.npmjs.org/react-native
# Résultat : JSON data ✅
```

---

## 📝 Résumé

| Élément | État | Notes |
| --- | --- | --- |
| **Metro Bundler** | ✅ Fonctionne | Port 8081 - Prêt |
| **Web Build** | ✅ Fonctionne | Port 8082 - Prêt |
| **Expo Go (Mobile)** | ✅ Fonctionne | Utiliser cette approche |
| **iOS Native Build** | ⚠️ Bloqué par Sandbox | Lever sandbox si nécessaire |
| **Android Native** | ⚠️ Non configuré | Première priorité : iOS |

---

## 💡 Recommandation

Pour **développement** : Continuez avec Expo Go + Metro + Web
Pour **publication** : Levez le sandbox dans Terminal Normal
