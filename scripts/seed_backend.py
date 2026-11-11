#!/usr/bin/env python3
import os
import django
from django.utils import timezone

ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(ROOT)
BACKEND_ROOT = os.path.join(PROJECT_ROOT, 'backend')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import sys
sys.path.insert(0, BACKEND_ROOT)

django.setup()

from api.models import NotificationGroup, Announcement, LiturgicalReading, MassRequest, UserProfile
from django.contrib.auth import get_user_model
from datetime import timedelta


def seed():
    print('Seeding groups...')
    groups = ['Chorale', 'JEC', 'CV-AV', 'Service d\'ordre']
    for name in groups:
        NotificationGroup.objects.get_or_create(name=name)

    print('Seeding announcements...')
    announcement_data = [
        ('Bans de mariage - première publication', 'Prions pour les couples qui se préparent au mariage et signalons toute opposition légitime au secrétariat paroissial.', 'ban_mariage', 'https://images.unsplash.com/photo-1519741497674-611481863552?w=1200&q=80'),
        ('Prière du CEB', 'Seigneur, rassemble nos communautés de base et fais de chaque foyer un lieu de paix, de service et de fraternité.', 'communique', 'https://images.unsplash.com/photo-1507692049790-de58290a4334?w=1200&q=80'),
        ('Annonce paroissiale', 'La messe communautaire est célébrée dimanche à 10h. Toute la paroisse est invitée à participer.', 'communique', 'https://images.unsplash.com/photo-1548625361-ec85e7e1d35c?w=1200&q=80'),
        ('Mouvement des jeunes', 'La rencontre JEC aura lieu samedi après-midi autour du thème : servir avec joie.', 'communique', 'https://images.unsplash.com/photo-1529156069898-49953e39b3ac?w=1200&q=80'),
        ('Chorale Sainte Cécile', 'Répétition de la chorale vendredi à 18h30. Les nouveaux choristes sont les bienvenus.', 'communique', 'https://images.unsplash.com/photo-1524368535928-5b5e00ddc76b?w=1200&q=80'),
        ('Catéchèse des enfants', 'Les inscriptions au parcours de catéchèse sont ouvertes auprès de la paroisse après chaque messe.', 'communique', 'https://images.unsplash.com/photo-1504159506876-f8338247a14a?w=1200&q=80'),
        ('Journée de prière', 'Une journée de prière et d’adoration est proposée pour confier les familles et les vocations.', 'communique', 'https://images.unsplash.com/photo-1473177104440-ffee2f376098?w=1200&q=80'),
        ('Avis aux servants d’autel', 'Réunion de préparation des servants d’autel samedi à 9h dans la salle paroissiale.', 'communique', 'https://images.unsplash.com/photo-1438032005730-c779502df39b?w=1200&q=80'),
        ('Collecte de solidarité', 'Une collecte de denrées est organisée pour soutenir les familles les plus fragiles de notre quartier.', 'communique', 'https://images.unsplash.com/photo-1559027615-cd4628902d4a?w=1200&q=80'),
        ('Fête patronale', 'Retrouvons-nous pour préparer la fête patronale dans la joie, la prière et le service.', 'communique', 'https://images.unsplash.com/photo-1504052434569-70ad5836ab65?w=1200&q=80'),
    ]
    for title, body, announcement_type, image_url in announcement_data:
        Announcement.objects.update_or_create(
            title=title,
            defaults={
                'body': body,
                'announcement_type': announcement_type,
                'image_url': image_url,
                'published_at': timezone.now(),
            },
        )

    print('Seeding mass requests...')
    User = get_user_model()
    demo_user, _ = User.objects.get_or_create(username='+221770000099')
    if not demo_user.has_usable_password():
        demo_user.set_password('demo123')
        demo_user.save(update_fields=['password'])
    demo_profile, _ = UserProfile.objects.get_or_create(
        user=demo_user,
        defaults={
            'phone_number': demo_user.username,
            'first_name': 'Utilisateur',
            'last_name': 'Démo',
            'otp_verified': True,
        },
    )
    for index, (message, days) in enumerate([
        ('Messe demandée pour la famille et les défunts.', 3),
        ('Action de grâce pour une naissance.', 7),
        ('Intention de prière pour la réussite aux examens.', 14),
    ], start=1):
        MassRequest.objects.get_or_create(
            requester=demo_profile,
            message=message,
            defaults={
                'phone': demo_user.username,
                'preferred_date': timezone.now() + timedelta(days=days),
                'status': 'pending',
            },
        )

    print('Seeding liturgical reading...')
    today = timezone.localdate()
    LiturgicalReading.objects.update_or_create(date=today, defaults={'title': 'Lecture du jour', 'content': 'Voici la lecture du jour.', 'source': 'Livre liturgique'})

    print('Done.')

if __name__ == '__main__':
    seed()
