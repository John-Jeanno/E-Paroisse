import api.models
import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0012_translate_all_admin_permissions'),
    ]

    operations = [
        migrations.AddField(
            model_name='announcement',
            name='video_url',
            field=models.URLField(blank=True, default='', verbose_name='adresse de la vidéo'),
        ),
        migrations.AddField(
            model_name='announcement',
            name='video_file',
            field=models.FileField(
                blank=True,
                help_text='Formats acceptés : MP4, M4V, MOV et WebM. Taille maximale : 100 Mo.',
                upload_to='announcements/videos/%Y/%m/',
                validators=[
                    django.core.validators.FileExtensionValidator(allowed_extensions=['mp4', 'm4v', 'mov', 'webm']),
                    api.models.validate_announcement_video_size,
                ],
                verbose_name='fichier vidéo',
            ),
        ),
    ]
