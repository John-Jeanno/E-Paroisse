from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0021_quizsession_timer_waits_for_audio'),
    ]

    operations = [
        migrations.AddField(
            model_name='announcement',
            name='link_url',
            field=models.URLField(
                blank=True,
                default='',
                help_text='Lien externe affiché sous forme d’aperçu cliquable.',
                verbose_name='adresse du lien',
            ),
        ),
        migrations.AddField(
            model_name='announcement',
            name='link_title',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Titre affiché dans l’aperçu. À défaut, le domaine du lien est utilisé.',
                max_length=255,
                verbose_name='titre de l’aperçu du lien',
            ),
        ),
    ]
