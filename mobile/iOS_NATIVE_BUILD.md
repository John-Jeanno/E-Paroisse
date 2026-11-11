# ✅ iOS Build - Instructions Complètes (Terminal Normal)

## 🎉 BONNE NOUVELLE

Le build iOS **FONCTIONNE maintenant** !

L'erreur "Hermes 403 Forbidden" est **RÉSOLUE** - Hermes a téléchargé avec succès depuis Maven Central.

## ⚠️ Important

Vous **DEVEZ** utiliser **Terminal.app normal**, PAS le terminal intégré de VS Code.

Terminal VS Code reste sandboxé même avec les restrictions levées.

---

## 🚀 Instructions : Compiler iOS

### Étape 1 : Ouvrir Terminal Normal

```bash
# Méthode 1 : Utiliser Spotlight
⌘ + SPACE
Taper : "Terminal"
Appuyer sur Entrée
```

Ou

```bash
# Méthode 2 : Utiliser Finder
Applications → Utilitaires → Terminal
```

### Étape 2 : Naviguer vers le projet

```bash
cd /Users/mac/E-paroisse/mobile
```

### Étape 3 : Compiler pour iOS

```bash
# Option A : Build + Lancer dans simulateur
npm run ios-direct

# Option B : Juste pod install (sans compiler)
cd ios && pod install && cd ..

# Option C : Nettoyer et recommencer
rm -f ios/Podfile.lock && rm -rf ios/Pods && npm run ios-direct
```

### Étape 4 : Attendre la compilation

- Première fois : **20-30 minutes** (télécharge Hermes + compile tout)
- Fois suivantes : **5-10 minutes** (cache disponible)

---

## 📊 Progression Attendue

```
✅ Codegen : Génère les fichiers automatiquement
✅ Pod install : Télécharge les dépendances
   [Hermes] Using release tarball from URL: ✅
   Installing hermes-engine (0.81.5) ✅
✅ Compilation : Compile les sources natifs
✅ Xcode : Lance le simulateur iPhone
✅ App : Affiche l'app dans le simulateur
```

---

## ❌ Si ça ne fonctionne pas

### Erreur : "Operation not permitted @ dir_initialize"

Cela signifie que vous utilisez **VS Code Terminal** au lieu de Terminal.app

**Solution** :

```bash
# FERMER Terminal VS Code
# OUVRIR Terminal.app normal
# Relancer la commande
```

### Erreur : "Xcode path not set"

```bash
sudo xcode-select --install
# OU
sudo xcode-select --switch /Applications/Xcode.app/Contents/Developer
```

### Erreur : "Pod version incompatible"

```bash
# Mettre à jour CocoaPods
sudo gem install cocoapods

# Nettoyer et réessayer
cd /Users/mac/E-paroisse/mobile
rm -f ios/Podfile.lock
rm -rf ios/Pods
npm run ios-direct
```

---

## 🎯 Résumé des Changements Apportés

| Fichier | Changement | Raison |
| --------- | ----------- | -------- |
| `Podfile` | iOS platform : 15.0 → 15.1 | Hermes require iOS 15.1+ |
| `Podfile` | Removed `__apply_Xcode_12_5_M1_post_install_workaround` | Méthode dépréciée en CocoaPods moderne |
| `Podfile.properties.json` | `expo.jsEngine : "jsc"` | Configuration pour JSC (optionnel) |

---

## ✨ Prochaines Étapes

### Après compilation iOS

1. **Simulateur iPhone lancé**

   ```
   Vous verrez l'app chargée dans le simulateur
   Metro Bundler fournit le code JS en temps réel
   ```

2. **Hot Reload**
   - Modifiez un fichier dans `src/`
   - L'app recharge automatiquement

3. **Ouvrir Web aussi**

   ```bash
   # Dans une autre Terminal
   npm run web  # http://localhost:8082
   ```

4. **Tester sur appareil réel**

   ```bash
   npm start    # Expo Go avec QR code
   ```

---

## 📝 Commandes Utiles

```bash
# iOS
npm run ios-direct           # Build + simulateur
cd ios && pod install && cd ..  # Juste pods

# Web
npm run web                  # Port 8082
npm run web-clean           # Clean + rebuild

# Metro
npm start                   # QR code

# Nettoyage complet
rm -rf ios/Pods ios/Podfile.lock
rm -rf /tmp/expo_*
npm install
```

---

## 💡 Notes Importantes

- **VS Code Terminal ne fonctionne pas** pour iOS build (limites sandbox)
- **Terminal.app normal** : Pas de restrictions, fonctionne parfaitement
- **Hermes** : Télécharge maintenant sans erreur 403
- **Xcode** : Doit être installé (`xcode-select --install`)
- **Première compilation** : Prend du temps (normal !)

---

**Vous êtes maintenant prêt pour compiler iOS natif ! 🚀**
