# Déploiement et configuration — E-paroisse

Ce document décrit les étapes essentielles pour déployer localement ou en production le backend Django et l'application mobile Expo.

## Variables d'environnement importantes

- `DJANGO_SECRET_KEY` — clé secrète Django
- `DJANGO_DEBUG` — `True` en dev, `False` en prod
- `DATABASE_URL` — (optionnel) pour config DB si vous utilisez autre chose que SQLite
- `PRIVATE_DOCUMENT_ROOT` — (optionnel) répertoire des pièces GED privées (par défaut `backend/private_documents`, distinct de `MEDIA_ROOT`)
- Email (pour notifications admin):
  - `EMAIL_BACKEND` — ex: `django.core.mail.backends.smtp.EmailBackend` ou `django.core.mail.backends.console.EmailBackend` (dev)
  - `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS` ou `EMAIL_USE_SSL`
  - `DEFAULT_FROM_EMAIL` — adresse expéditrice
  - `ADMINS` — liste d'administrateurs (pour `mail_admins`) si souhaité

## Backend — Django

1. Créer et activer l'environnement virtuel:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

1. Charger les variables d'environnement (par ex `.env`) et initialiser la base:

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py loaddata initial_data.json  # si vous avez des fixtures
```

1. Créer un superuser:

```bash
python manage.py createsuperuser
```

1. Lancer le serveur de développement:

```bash
python manage.py runserver 0.0.0.0:8000
```

1. Tests:

```bash
python manage.py test
```

Notes:

- Pour les notifications de nouvelles `MassRequest`, configurez `EMAIL_BACKEND` et `DEFAULT_FROM_EMAIL`. Le signal tente d'envoyer un email aux utilisateurs `is_staff` ayant une adresse email, sinon utilise `mail_admins`.
- En développement, utilisez `EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend` pour afficher les emails dans la console.
- Sauvegardez ensemble la base de données et `PRIVATE_DOCUMENT_ROOT` : la base contient les références aux fichiers GED stockés séparément.
- Les pièces GED ne sont pas publiées sous `MEDIA_URL`. Leur téléchargement passe par l'administration avec authentification et vérification de permissions.
- Pour le rôle secrétariat, attribuez les permissions de consultation/création/modification des documents et modèles. Pour le rôle prêtre valideur, ajoutez `Can validate and archive parish documents`; pour les dossiers finances, sacramentels et personnel, ajoutez `Can view confidential parish documents`.

## Mobile — Expo (React Native)

Le client mobile natif, le site Web et la PWA partagent le même code Expo.
Un déploiement Docker reconstruit le site Web/PWA; le conteneur backend applique
les migrations Django au démarrage. Les applications Android/iOS déjà installées
ne sont pas mises à jour par ce déploiement Web : elles nécessitent un nouveau
build natif et sa distribution sur les appareils.

1. Installer dépendances et lancer Metro:

```bash
cd mobile
npm install
npx expo start
```

1. Pour tester TypeScript sans exécuter l'app:

```bash
npx tsc --noEmit
```

1. Variables / configuration d'API

- Assurez-vous que `mobile/src/api/apiClient.ts` ou équivalent pointe vers l'URL API correcte (`http://<host>:8000/api/`) ou utilisez `REACT_NATIVE_APP_API_URL`.
- Après une modification mobile/Web, vérifiez TypeScript et reconstruisez le bundle Web/PWA avec `npx expo export --platform web`. Le build Docker de production exécute aussi cette commande.

## Déploiement en production (résumé)

- Utiliser une base de données robuste (Postgres) et configurer `DATABASES` via `DATABASE_URL`.
- Configurer un serveur d'applications (Gunicorn, Daphne/ASGI si websockets), reverse proxy (Nginx).
- Configurer un stockage de fichiers (S3) pour `MEDIA_URL`/`MEDIA_ROOT` en production.
- Configurer sécurité: `DEBUG=False`, `ALLOWED_HOSTS`, HTTPS, CSP, etc.
- Configurer une solution d'envoi d'emails (SendGrid, SMTP) et définir `DEFAULT_FROM_EMAIL` et `ADMINS`.

## Commandes utiles rapides

```bash
# backend
cd backend
source .venv/bin/activate
python manage.py migrate
python manage.py runserver

# mobile
cd mobile
npm install
npx expo start
```

## Points d'attention et améliorations recommandées

- Ajouter une notification interne persistante (modèle `AdminNotification`) si vous souhaitez historiser les alertes côté admin.
- Ajouter validations côté serveur pour `preferred_date` et `message` (taille maximale).
- Ajouter tests unitaires et d'intégration pour l'API `MassRequest`.
- Mettre en place CI: tests backend et compilation TypeScript mobile.

## Déploiement Docker isolé sur VPS

Le fichier `docker-compose.yml` déploie le site Expo web et l'API Django sur un réseau Docker dédié. Seul le port hôte `18080` est publié; il sert HTTPS avec le certificat Let's Encrypt du VPS `5szq.l.time4vps.cloud`. La base SQLite, les médias et les documents privés sont conservés dans des volumes Docker nommés. Les données locales et le fichier `backend/.env` ne doivent pas être copiés sur le VPS.

1. Créer `deploy/runtime.env` sur le serveur avec une valeur aléatoire forte pour `DJANGO_SECRET_KEY`, `DJANGO_CSRF_TRUSTED_ORIGINS=https://5szq.l.time4vps.cloud:18080` et les paramètres de paiement souhaités. Garder ce fichier lisible uniquement par l'administrateur.
2. Vérifier que les certificats sont présents dans `/etc/letsencrypt/live/5szq.l.time4vps.cloud/` et dans `/etc/letsencrypt/archive/5szq.l.time4vps.cloud-0001/`. Ils sont montés en lecture seule dans le conteneur web.
3. Depuis la racine du projet, construire et lancer les conteneurs avec `docker compose up -d --build`.
4. Créer un compte administrateur avec `docker compose exec backend python manage.py createsuperuser`.
5. Vérifier `docker compose ps`, les journaux, l'API `/api/annonces/` et l'administration `/admin/` via HTTPS. Le renouvellement automatique du certificat doit recharger Nginx.

Sur ce VPS, installer un hook Certbot deploy qui recharge le seul Nginx de cette application lorsque le certificat de `5szq.l.time4vps.cloud` est renouvelé; ne pas modifier le reverse proxy partagé des autres applications.

Accès sécurisé : `https://5szq.l.time4vps.cloud:18080/`. Le port hôte `18080` parle TLS; utilisez bien `https://`, et non `http://`. Les ports `80`, `443` et `18081` utilisés par d'autres applications ne sont pas modifiés. HSTS n'est volontairement pas activé, car ce nom d'hôte est partagé sur le VPS et HSTS affecterait l'ensemble du nom, pas seulement ce port.

---
Si vous voulez, je peux ajouter un fichier d'exemple `.env.example` et une workflow GitHub Actions pour exécuter les tests CI. Voulez-vous ça aussi ?
