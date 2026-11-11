import json
from pathlib import Path

from django.db import migrations


def seed_verse_questions(apps, schema_editor):
    Question = apps.get_model('api', 'QuizQuestion')
    data_path = Path(__file__).resolve().parent.parent / 'data' / 'catholic_bible_verse_questions.json'
    with data_path.open(encoding='utf-8') as question_file:
        rows = json.load(question_file)

    Question.objects.bulk_create([
        Question(
            testament=row['testament'],
            category=row['category'],
            prompt=row['prompt'],
            options=row['options'],
            correct_option=row['correct_option'],
            explanation=row['explanation'],
            is_active=True,
        )
        for row in rows
    ], batch_size=250)


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0019_quiz_challenge_notifications'),
    ]

    operations = [
        migrations.RunPython(seed_verse_questions, migrations.RunPython.noop),
    ]
