import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0018_catholic_bible_quiz_bank'),
    ]

    operations = [
        migrations.CreateModel(
            name='QuizChallengeNotification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('kind', models.CharField(choices=[('invitation', 'Invitation reçue'), ('accepted', 'Défi accepté'), ('declined', 'Défi refusé')], max_length=12)),
                ('is_read', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('actor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='quiz_notifications_sent', to='api.userprofile')),
                ('challenge', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to='api.quizchallenge')),
                ('recipient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='quiz_notifications', to='api.userprofile')),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.AddConstraint(
            model_name='quizchallengenotification',
            constraint=models.UniqueConstraint(fields=('recipient', 'challenge', 'kind'), name='unique_quiz_notification_event'),
        ),
    ]
