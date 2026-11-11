# E-Paroisse

Application mobile dédiée aux paroisses catholiques du Sénégal.

## Architecture

- `mobile/` : React Native app (Expo) pour les fidèles.
- `backend/` : Django REST API pour la gestion des profils, annonces, liturgie et notifications segmentées.

## Fonctionnalités clés

- Authentification par téléphone + OTP.
- Profils rattachés à une ou plusieurs entités paroissiales.
- Messagerie privée et conversations par entité avec recherche d'utilisateurs, messages écrits et messages vocaux (enregistrement limité à deux minutes, lecture et réponses).
- Horaires récurrents et dates particulières des messes, publiés par le secrétariat.
- Rubrique de dons Wave et Orange Money alimentée par les coordonnées de paiement renseignées par le secrétariat.
- Fil d'actualité, annonces, notifications segmentées et recherche globale dans les publications visibles, la liturgie, la catéchèse, le quiz et l'annuaire paroissial.
- Module liturgie avec lectures du jour et cache hors-ligne.
- Catéchèse illustrée avec 24 leçons guidées et jeu biblique en mode écrit ou audio. La banque contient 1 103 questions, dont 1 000 questions à trous fondées sur 1 000 versets distincts de la Bible catholique Crampon (1923, domaine public) et couvrant les 73 livres du canon catholique. Chaque série tire aléatoirement cinq questions de chaque Testament.
- Défis bibliques entre paroissiens : listes séparées des défis reçus et envoyés, notifications persistantes d’invitation et de réponse, 10 questions communes, 90 secondes par joueur, pause et reprise, sauvegarde de la progression, score final et revanche.
- Administration Django pour gérer les profils, publier ou retirer des annonces, traiter les demandes de messe et archiver les documents de la paroisse.

### Utilisation hors connexion

Connectez-vous une première fois en ligne et laissez les écrans charger pour mettre en cache les annonces, lectures, contacts, conversations et le pack du quiz. La PWA doit également avoir été ouverte en ligne au moins une fois afin que son shell soit stocké sur l’appareil. Les réponses GET déjà consultées sont mises en cache localement et séparées par compte.

Les demandes de messe, messages écrits privés et de groupe, commentaires, réactions aux annonces, partages et résultats de quiz solo écrits sont conservés dans une file locale avant leur envoi. Les messages vocaux nécessitent une connexion et ne sont pas placés dans cette file. À la reconnexion, les actions prises en charge sont synchronisées séquentiellement; une clé idempotente évite de créer un doublon lorsque le serveur a accepté une action avant une coupure.

Les brouillons des formulaires de demande de messe, de messagerie et de commentaire sont sauvegardés localement. Le quiz solo hors ligne utilise dix questions préchargées et n’a pas de chronomètre. L’authentification initiale, les défis en ligne, le quiz audio, les paiements, les messages vocaux et les téléversements de médias nécessitent une connexion. Le contenu non encore consulté ou préchargé n’est pas garanti disponible hors ligne.

### Gestion paroissiale dans l'administration Django

La banque de versets à trous provient de la Bible Crampon (édition catholique de 1923, domaine public). Les questions sont générées à partir de versets distincts et affichent leur référence biblique.

Connectez-vous à `/admin/` avec un compte administrateur Django. L’interface et les libellés de gestion sont en français. Dans les listes :

- **Annonces** : recherchez par titre ou contenu, joignez une image par URL ou un média par fichier (MP4, M4V, MOV, WebM, JPG, JPEG ou PNG, 100 Mo maximum), ajoutez un lien externe avec son titre d'aperçu, puis publiez ou retirez plusieurs annonces à la fois. Le fil présente les publications les plus récentes d'abord, avec commandes de lecture vidéo et aperçu de lien cliquable.
- **Commentaires** : les commentaires des annonces sont consultables dans le fil; seuls les fidèles disposant d’un compte paroissial et connectés peuvent en publier. Le secrétariat peut les consulter et les modérer depuis l’administration.
- **Entités paroissiales et messagerie** : les profils peuvent appartenir à plusieurs entités et l’historique collectif est filtré selon ces appartenances. La messagerie privée permet de rechercher un paroissien vérifié par son nom ; les vocaux sont servis par des routes authentifiées.
- **Horaires de messe** : publiez des horaires récurrents par jour de semaine ou des dates particulières, avec l’heure et le lieu. Les horaires actifs sont affichés aux fidèles.
- **Dons** : renseignez les identifiants Wave et Orange Money ainsi que les instructions. L’application affiche ces coordonnées, mais ne traite ni ne confirme automatiquement les transactions ; cette configuration n’est pas un paiement intégré.
- **Demandes de messe** : filtrez par statut et date, recherchez par coordonnées ou nom du demandeur, puis acceptez ou refusez plusieurs demandes à la fois.
- **GED paroissiale** : classez les fichiers et textes par catégorie, type, date et référence. Les catégories finances, sacrements et personnel sont confidentielles et réservées aux comptes auxquels la permission dédiée a été accordée.
- **Documents courants** : rédigez le contenu dans l’admin, puis téléchargez-le au format Word (.docx). Les fichiers déposés restent privés et ne sont servis qu’aux comptes autorisés.
- **Modèles réutilisables** : créez des modèles de courriers, attestations, comptes rendus, annonces et formulaires ; utilisez « Créer depuis ce modèle » pour démarrer un document prérempli.
- **Workflow** : brouillon → à valider → validé → archivé. Les validateurs ne peuvent pas valider leurs propres documents ; toute modification après soumission réinitialise la validation.

Deux groupes de permissions sont créés à la migration : **Secrétariat paroissial** (création, classement et soumission) et **Prêtres** (mêmes droits, validation et accès confidentiel). Dans l’administration Django, ouvrez les comptes du personnel et attribuez-leur le groupe correspondant. Les catégories finances, sacrements, personnel et les actes sacramentels restent confidentiels par défaut.

## Setup rapide

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### Mobile

```bash
cd mobile
npm install
npx expo start
```

Les builds natifs de production utilisent l'API HTTPS de la paroisse. En développement, Expo continue d'utiliser l'hôte local du serveur. Le site installable (PWA) est publié sur `https://5szq.l.time4vps.cloud:18080/` et utilise la même API.

Pour générer un APK Android arm64 de test :

```bash
cd mobile/android
./gradlew -PreactNativeArchitectures=arm64-v8a assembleRelease
```

Le fichier est généré dans `mobile/android/app/build/outputs/apk/release/app-release.apk`. La configuration actuelle signe les builds Android avec la clé debug : cet APK convient au test et à l'installation manuelle, mais pas à une publication ou une mise à jour Play Store. Une version native iOS doit être signée avec le compte Apple et le profil de provisionnement de l'application avant de pouvoir être installée sur un iPhone ou publiée.

### Simulation locale sans mobile

Après avoir démarré le backend Django sur `http://127.0.0.1:8000` :

```bash
cd /Users/mac/E-paroisse
backend/.venv/bin/python3 scripts/simulate_mobile.py
```

Cela simule l'app mobile locale en demandant un OTP, en le vérifiant et en uploadant une image de test.

## Notes

- Adapter le service SMS/WhatsApp pour l'OTP selon les fournisseurs locaux.
- Prévoir une stratégie de compression d'images côté mobile et backend.
- Garder la base mobile légère avec un ciblage strict des dépendances.
