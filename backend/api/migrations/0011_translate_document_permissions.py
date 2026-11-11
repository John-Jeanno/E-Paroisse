from django.db import migrations


PERMISSION_NAMES = {
    'add_parishdocument': 'Peut ajouter un document paroissial',
    'change_parishdocument': 'Peut modifier un document paroissial',
    'view_parishdocument': 'Peut consulter les documents paroissiaux',
    'approve_parishdocument': 'Peut valider et archiver les documents paroissiaux',
    'view_sensitive_parishdocument': 'Peut consulter les documents paroissiaux confidentiels',
    'add_parishdocumenttemplate': 'Peut ajouter un modèle de document paroissial',
    'change_parishdocumenttemplate': 'Peut modifier un modèle de document paroissial',
    'view_parishdocumenttemplate': 'Peut consulter les modèles de documents paroissiaux',
}


def translate_permission_names(apps, schema_editor):
    Permission = apps.get_model('auth', 'Permission')
    for codename, name in PERMISSION_NAMES.items():
        Permission.objects.filter(
            content_type__app_label='api',
            codename=codename,
        ).update(name=name)


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0010_alter_parishdocumentworkflowevent_options_and_more'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunPython(translate_permission_names, migrations.RunPython.noop),
    ]
