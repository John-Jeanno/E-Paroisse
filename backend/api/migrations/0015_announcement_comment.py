import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0014_announcement_media_file'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AnnouncementComment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('body', models.TextField(max_length=2000, verbose_name='commentaire')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='publié le')),
                ('announcement', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='comments',
                    to='api.announcement',
                    verbose_name='annonce',
                )),
                ('author', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='announcement_comments',
                    to='api.userprofile',
                    verbose_name='auteur',
                )),
            ],
            options={
                'verbose_name': 'commentaire d’annonce',
                'verbose_name_plural': 'commentaires des annonces',
                'ordering': ['created_at'],
            },
        ),
    ]
