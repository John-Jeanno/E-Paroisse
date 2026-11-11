from django.db import migrations


def translate_permissions(apps, schema_editor):
    from api.admin_localization import translate_admin_permission_names

    translate_admin_permission_names(app_registry=apps, using=schema_editor.connection.alias)


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0011_translate_document_permissions'),
    ]

    operations = [
        migrations.RunPython(translate_permissions, migrations.RunPython.noop),
    ]
