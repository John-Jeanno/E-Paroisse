import api.models
import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0013_announcement_video'),
    ]

    operations = [
        migrations.RenameField(
            model_name='announcement',
            old_name='video_file',
            new_name='media_file',
        ),
        migrations.AlterField(
            model_name='announcement',
            name='media_file',
            field=models.FileField(
                blank=True,
                help_text='Formats acceptés : MP4, M4V, MOV, WebM, JPG, JPEG et PNG. Taille maximale : 100 Mo.',
                upload_to='announcements/media/%Y/%m/',
                validators=[
                    django.core.validators.FileExtensionValidator(
                        allowed_extensions=['mp4', 'm4v', 'mov', 'webm', 'jpg', 'jpeg', 'png']
                    ),
                    api.models.validate_announcement_media_size,
                ],
                verbose_name='fichier média',
            ),
        ),
    ]
