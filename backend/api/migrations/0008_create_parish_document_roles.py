from django.db import migrations


def create_parish_document_roles(apps, schema_editor):
    ContentType = apps.get_model('contenttypes', 'ContentType')
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')

    role_permissions = {
        'Secrétariat paroissial': {
            'parishdocument': ('add_parishdocument', 'change_parishdocument', 'view_parishdocument'),
            'parishdocumenttemplate': (
                'add_parishdocumenttemplate',
                'change_parishdocumenttemplate',
                'view_parishdocumenttemplate',
            ),
        },
        'Prêtres': {
            'parishdocument': (
                'add_parishdocument',
                'change_parishdocument',
                'view_parishdocument',
                'approve_parishdocument',
                'view_sensitive_parishdocument',
            ),
            'parishdocumenttemplate': (
                'add_parishdocumenttemplate',
                'change_parishdocumenttemplate',
                'view_parishdocumenttemplate',
            ),
        },
    }
    permission_names = {
        'add_parishdocument': 'Can add parish document',
        'change_parishdocument': 'Can change parish document',
        'view_parishdocument': 'Can view parish document',
        'approve_parishdocument': 'Can validate and archive parish documents',
        'view_sensitive_parishdocument': 'Can view confidential parish documents',
        'add_parishdocumenttemplate': 'Can add parish document template',
        'change_parishdocumenttemplate': 'Can change parish document template',
        'view_parishdocumenttemplate': 'Can view parish document template',
    }

    for group_name, model_permissions in role_permissions.items():
        group, _ = Group.objects.get_or_create(name=group_name)
        for model_name, codenames in model_permissions.items():
            content_type, _ = ContentType.objects.get_or_create(
                app_label='api',
                model=model_name,
            )
            permissions = []
            for codename in codenames:
                permission, _ = Permission.objects.get_or_create(
                    content_type=content_type,
                    codename=codename,
                    defaults={'name': permission_names[codename]},
                )
                permissions.append(permission)
            group.permissions.add(*permissions)


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0007_parishdocumenttemplate_parishdocument_template'),
        ('auth', '0012_alter_user_first_name_max_length'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.RunPython(create_parish_document_roles, migrations.RunPython.noop),
    ]
