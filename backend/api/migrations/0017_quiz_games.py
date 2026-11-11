import django.db.models.deletion
from django.db import migrations, models


QUESTIONS = [
    ('ancien', 'Personnages', 'Selon le récit de la création, quel jour Dieu créa-t-il l’être humain ?', ['Le troisième jour', 'Le sixième jour', 'Le septième jour'], 1, 'Le récit place la création de l’homme et de la femme au sixième jour (Genèse 1,26-31).'),
    ('ancien', 'Récits', 'Quel signe Noé voit-il après le déluge comme promesse de Dieu ?', ['Un arc-en-ciel', 'Une étoile filante', 'Une colombe dorée'], 0, 'L’arc-en-ciel est le signe de l’alliance de Dieu avec la terre (Genèse 9,12-17).'),
    ('ancien', 'Patriarches', 'Comment s’appelle le fils que Sara donne à Abraham ?', ['Ismaël', 'Isaac', 'Jacob'], 1, 'Isaac naît selon la promesse faite à Abraham et Sara (Genèse 21,1-3).'),
    ('ancien', 'Personnages', 'Quel jeune hébreu interpréta les rêves du pharaon en Égypte ?', ['Joseph', 'Josué', 'Samuel'], 0, 'Joseph interpréta les rêves du pharaon et conseilla de préparer des réserves (Genèse 41).'),
    ('ancien', 'Exode', 'Où la mère de Moïse déposa-t-elle son bébé pour le protéger ?', ['Dans une grotte', 'Dans une corbeille sur le Nil', 'Dans le temple'], 1, 'Elle plaça Moïse dans une corbeille enduite de bitume, parmi les roseaux du Nil (Exode 2,3).'),
    ('ancien', 'Exode', 'Quel chemin Dieu ouvrit-il pour permettre aux Israélites de fuir l’Égypte ?', ['À travers la mer', 'À travers le désert de glace', 'À travers une montagne'], 0, 'Moïse étendit sa main et les eaux de la mer s’ouvrirent (Exode 14,21-22).'),
    ('ancien', 'Loi', 'Sur quelle montagne Moïse reçut-il les commandements ?', ['Le mont Carmel', 'Le mont Sinaï', 'Le mont des Oliviers'], 1, 'Moïse monta sur le Sinaï, où Dieu lui donna les paroles de l’alliance (Exode 19–20).'),
    ('ancien', 'Conquête', 'Quelle ville Josué et le peuple prirent-ils après en avoir fait le tour ?', ['Jéricho', 'Bethléem', 'Ninive'], 0, 'Les murailles de Jéricho tombèrent après que le peuple eut suivi les instructions reçues (Josué 6).'),
    ('ancien', 'Personnages', 'Comment s’appelle la belle-mère de Ruth ?', ['Déborah', 'Naomi', 'Abigaïl'], 1, 'Ruth resta auprès de Naomi et partit avec elle vers Bethléem (Ruth 1,16-19).'),
    ('ancien', 'Rois', 'Quel adversaire David vainquit-il avec une fronde ?', ['Goliath', 'Saül', 'Absalom'], 0, 'David affronta Goliath avec une fronde et une pierre (1 Samuel 17,48-50).'),
    ('ancien', 'Rois', 'Que demanda Salomon à Dieu au début de son règne ?', ['La sagesse', 'Une longue vie', 'Une grande armée'], 0, 'Salomon demanda un cœur attentif pour gouverner le peuple avec discernement (1 Rois 3,9-12).'),
    ('ancien', 'Prophètes', 'Sur quelle montagne Élie affronta-t-il les prophètes de Baal ?', ['Le mont Sinaï', 'Le mont Carmel', 'Le mont Nébo'], 1, 'Le défi entre Élie et les prophètes de Baal eut lieu sur le Carmel (1 Rois 18,19-39).'),
    ('ancien', 'Prophètes', 'Dans quel lieu Daniel fut-il jeté puis protégé par Dieu ?', ['Une fosse aux lions', 'Une fournaise', 'Une citerne vide'], 0, 'Dieu ferma la gueule des lions et Daniel fut retrouvé vivant (Daniel 6,17-24).'),
    ('ancien', 'Personnages', 'Quelle reine risqua sa vie pour défendre son peuple ?', ['Esther', 'Jézabel', 'Vasthi'], 0, 'Esther se présenta devant le roi pour intercéder en faveur de son peuple (Esther 4,16; 7,3-4).'),
    ('ancien', 'Prophètes', 'Quel prophète fut envoyé à Ninive après avoir été avalé par un grand poisson ?', ['Jonas', 'Amos', 'Ézéchiel'], 0, 'Jonas pria dans le ventre du poisson puis reçut à nouveau la mission d’aller à Ninive (Jonas 2–3).'),
    ('nouveau', 'Vie de Jésus', 'Dans quelle ville Jésus est-il né ?', ['Nazareth', 'Bethléem', 'Capharnaüm'], 1, 'Jésus naquit à Bethléem, la ville de David (Matthieu 2,1; Luc 2,4-7).'),
    ('nouveau', 'Vie de Jésus', 'Dans quel fleuve Jésus fut-il baptisé par Jean ?', ['Le Jourdain', 'Le Nil', 'L’Euphrate'], 0, 'Jean baptisa Jésus dans le Jourdain (Matthieu 3,13-17).'),
    ('nouveau', 'Miracles', 'Quel fut le premier signe de Jésus à Cana ?', ['Il changea l’eau en vin', 'Il calma une tempête', 'Il guérit un aveugle'], 0, 'À Cana, Jésus changea l’eau en vin lors d’un mariage (Jean 2,1-11).'),
    ('nouveau', 'Disciples', 'Quel métier exerçaient Simon Pierre et André avant de suivre Jésus ?', ['Pêcheurs', 'Collecteurs d’impôts', 'Charpentiers'], 0, 'Simon et André jetaient leurs filets dans la mer lorsqu’ils furent appelés (Marc 1,16-18).'),
    ('nouveau', 'Paraboles', 'Dans la parabole de Jésus, qui s’arrête pour aider l’homme blessé sur la route ?', ['Un Samaritain', 'Un soldat romain', 'Un marchand'], 0, 'Le Samaritain fut ému de compassion, s’approcha et prit soin du blessé (Luc 10,33-35).'),
    ('nouveau', 'Miracles', 'Avec quoi Jésus nourrit-il une foule de cinq mille hommes ?', ['Cinq pains et deux poissons', 'Sept pains et trois poissons', 'Du pain et des raisins'], 0, 'Jésus bénit cinq pains et deux poissons, qui nourrirent la foule (Jean 6,9-13).'),
    ('nouveau', 'Personnages', 'Dans quel arbre Zachée grimpa-t-il pour voir Jésus ?', ['Un sycomore', 'Un olivier', 'Un cèdre'], 0, 'Zachée monta sur un sycomore parce qu’il était petit et que la foule le gênait (Luc 19,3-4).'),
    ('nouveau', 'Miracles', 'Quel ami de Jésus fut rappelé à la vie après quatre jours au tombeau ?', ['Lazare', 'Étienne', 'Bartimée'], 0, 'Jésus appela Lazare hors du tombeau à Béthanie (Jean 11,38-44).'),
    ('nouveau', 'Passion', 'Pour combien de pièces d’argent Judas livra-t-il Jésus ?', ['Trente', 'Dix', 'Cinquante'], 0, 'Judas reçut trente pièces d’argent pour livrer Jésus (Matthieu 26,14-16).'),
    ('nouveau', 'Passion', 'Combien de fois Pierre renia-t-il Jésus avant le chant du coq ?', ['Une fois', 'Trois fois', 'Cinq fois'], 1, 'Pierre renia Jésus trois fois, comme Jésus l’avait annoncé (Luc 22,54-62).'),
    ('nouveau', 'Résurrection', 'Quand les femmes découvrirent-elles le tombeau de Jésus vide ?', ['Le premier jour de la semaine, à l’aube', 'Le jour du sabbat, à midi', 'Une semaine après'], 0, 'Les femmes vinrent au tombeau à l’aube du premier jour de la semaine (Luc 24,1-6).'),
    ('nouveau', 'Église primitive', 'Quel événement les disciples célébrèrent-ils à Jérusalem lorsque l’Esprit Saint descendit sur eux ?', ['La Pentecôte', 'La Pâque', 'La Dédicace'], 0, 'À la Pentecôte, les disciples furent remplis de l’Esprit Saint (Actes 2,1-4).'),
    ('nouveau', 'Apôtres', 'Dans quelle ville Saul se rendait-il lorsque Jésus se révéla à lui ?', ['Damas', 'Rome', 'Antioche'], 0, 'Saul était en route vers Damas lorsqu’une lumière l’enveloppa et qu’il entendit Jésus (Actes 9,1-6).'),
    ('nouveau', 'Église primitive', 'Quel métier exerçait Lydie, que Paul rencontra à Philippes ?', ['Marchande de pourpre', 'Tisseuse de lin', 'Potière'], 0, 'Lydie était marchande de pourpre et accueillit Paul et ses compagnons (Actes 16,14-15).'),
    ('nouveau', 'Apôtres', 'Quel jeune collaborateur de Paul était le fils d’une mère juive croyante et d’un père grec ?', ['Timothée', 'Tite', 'Silas'], 0, 'Timothée avait une mère juive croyante et un père grec (Actes 16,1-3).'),
]


def seed_questions(apps, schema_editor):
    Question = apps.get_model('api', 'QuizQuestion')
    Question.objects.bulk_create([
        Question(
            testament=testament,
            category=category,
            prompt=prompt,
            options=options,
            correct_option=correct_option,
            explanation=explanation,
            is_active=True,
        )
        for testament, category, prompt, options, correct_option, explanation in QUESTIONS
    ])


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0016_announcementshare_announcementlike'),
    ]

    operations = [
        migrations.CreateModel(
            name='QuizChallenge',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('pending', 'En attente'), ('active', 'En cours'), ('declined', 'Refusée'), ('completed', 'Terminée'), ('expired', 'Expirée')], default='pending', max_length=10, verbose_name='état')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='créée le')),
                ('accepted_at', models.DateTimeField(blank=True, null=True, verbose_name='acceptée le')),
                ('completed_at', models.DateTimeField(blank=True, null=True, verbose_name='terminée le')),
                ('challenger', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='quiz_challenges_sent', to='api.userprofile')),
                ('recipient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='quiz_challenges_received', to='api.userprofile')),
            ],
            options={'ordering': ['-created_at'], 'verbose_name': 'défi biblique', 'verbose_name_plural': 'défis bibliques'},
        ),
        migrations.CreateModel(
            name='QuizQuestion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('testament', models.CharField(choices=[('ancien', 'Ancien Testament'), ('nouveau', 'Nouveau Testament')], max_length=10, verbose_name='testament')),
                ('category', models.CharField(max_length=100, verbose_name='catégorie')),
                ('prompt', models.CharField(max_length=500, verbose_name='question')),
                ('options', models.JSONField(verbose_name='choix de réponse')),
                ('correct_option', models.PositiveSmallIntegerField(verbose_name='bonne réponse')),
                ('explanation', models.CharField(max_length=500, verbose_name='explication')),
                ('is_active', models.BooleanField(default=True, verbose_name='active')),
            ],
            options={'ordering': ['id'], 'verbose_name': 'question biblique', 'verbose_name_plural': 'questions bibliques'},
        ),
        migrations.CreateModel(
            name='QuizSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mode', models.CharField(choices=[('text', 'Texte'), ('audio', 'Audio')], max_length=10, verbose_name='mode')),
                ('status', models.CharField(choices=[('active', 'En cours'), ('paused', 'En pause'), ('completed', 'Terminée')], default='active', max_length=10, verbose_name='état')),
                ('current_index', models.PositiveSmallIntegerField(default=0, verbose_name='question actuelle')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='créée le')),
                ('completed_at', models.DateTimeField(blank=True, null=True, verbose_name='terminée le')),
                ('profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='quiz_sessions', to='api.userprofile')),
            ],
            options={'ordering': ['-created_at'], 'verbose_name': 'partie individuelle', 'verbose_name_plural': 'parties individuelles'},
        ),
        migrations.CreateModel(
            name='QuizChallengeParticipant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('current_index', models.PositiveSmallIntegerField(default=0)),
                ('remaining_seconds', models.PositiveSmallIntegerField(default=90)),
                ('timer_started_at', models.DateTimeField(blank=True, null=True)),
                ('is_paused', models.BooleanField(default=True)),
                ('finished_at', models.DateTimeField(blank=True, null=True)),
                ('timed_out', models.BooleanField(default=False)),
                ('challenge', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='participants', to='api.quizchallenge')),
                ('profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='quiz_challenge_participations', to='api.userprofile')),
            ],
        ),
        migrations.CreateModel(
            name='QuizChallengeQuestion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('position', models.PositiveSmallIntegerField()),
                ('challenge', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='challenge_questions', to='api.quizchallenge')),
                ('question', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='challenge_questions', to='api.quizquestion')),
            ],
            options={'ordering': ['position']},
        ),
        migrations.CreateModel(
            name='QuizSessionQuestion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('position', models.PositiveSmallIntegerField()),
                ('remaining_seconds', models.PositiveSmallIntegerField(default=40)),
                ('timer_started_at', models.DateTimeField(blank=True, null=True)),
                ('question', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='session_questions', to='api.quizquestion')),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='session_questions', to='api.quizsession')),
            ],
            options={'ordering': ['position']},
        ),
        migrations.CreateModel(
            name='QuizSessionResponse',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('option_index', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('is_correct', models.BooleanField(default=False)),
                ('timed_out', models.BooleanField(default=False)),
                ('answered_at', models.DateTimeField(auto_now_add=True)),
                ('session_question', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='response', to='api.quizsessionquestion')),
            ],
        ),
        migrations.CreateModel(
            name='QuizChallengeResponse',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('option_index', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('is_correct', models.BooleanField(default=False)),
                ('timed_out', models.BooleanField(default=False)),
                ('answered_at', models.DateTimeField(auto_now_add=True)),
                ('challenge_question', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='responses', to='api.quizchallengequestion')),
                ('participant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='responses', to='api.quizchallengeparticipant')),
            ],
        ),
        migrations.AddConstraint(
            model_name='quizchallenge',
            constraint=models.CheckConstraint(condition=models.Q(('challenger', models.F('recipient')), _negated=True), name='quiz_challenge_not_self'),
        ),
        migrations.AddConstraint(
            model_name='quizchallengeparticipant',
            constraint=models.UniqueConstraint(fields=('challenge', 'profile'), name='unique_quiz_challenge_participant'),
        ),
        migrations.AddConstraint(
            model_name='quizchallengequestion',
            constraint=models.UniqueConstraint(fields=('challenge', 'position'), name='unique_quiz_challenge_position'),
        ),
        migrations.AddConstraint(
            model_name='quizchallengequestion',
            constraint=models.UniqueConstraint(fields=('challenge', 'question'), name='unique_quiz_challenge_question'),
        ),
        migrations.AddConstraint(
            model_name='quizsessionquestion',
            constraint=models.UniqueConstraint(fields=('session', 'position'), name='unique_quiz_session_position'),
        ),
        migrations.AddConstraint(
            model_name='quizsessionquestion',
            constraint=models.UniqueConstraint(fields=('session', 'question'), name='unique_quiz_session_question'),
        ),
        migrations.AddConstraint(
            model_name='quizchallengeresponse',
            constraint=models.UniqueConstraint(fields=('participant', 'challenge_question'), name='unique_quiz_challenge_response'),
        ),
        migrations.RunPython(seed_questions, migrations.RunPython.noop),
    ]
