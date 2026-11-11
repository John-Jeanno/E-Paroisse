_PERMISSION_OBJECTS = {
    ('admin', 'logentry'): 'une entrée au journal',
    ('api', 'announcement'): 'une annonce',
    ('api', 'announcementcomment'): 'un commentaire d’annonce',
    ('api', 'liturgicalreading'): 'une lecture liturgique',
    ('api', 'massrequest'): 'une demande de messe',
    ('api', 'notificationgroup'): 'un groupe paroissial',
    ('api', 'otprequest'): 'une demande de code de vérification',
    ('api', 'parishdocument'): 'un document paroissial',
    ('api', 'parishdocumenttemplate'): 'un modèle de document paroissial',
    ('api', 'parishdocumentworkflowevent'): 'une étape du circuit de validation',
    ('api', 'privatemessage'): 'un message privé',
    ('api', 'userprofile'): 'un profil paroissial',
    ('auth', 'group'): 'un groupe',
    ('auth', 'permission'): 'une autorisation',
    ('auth', 'user'): 'un compte utilisateur',
    ('authtoken', 'token'): 'un jeton d’accès',
    ('authtoken', 'tokenproxy'): 'un jeton d’accès',
    ('contenttypes', 'contenttype'): 'un type de contenu',
    ('sessions', 'session'): 'une session',
}

_ACTIONS = {
    'add': 'Peut ajouter',
    'change': 'Peut modifier',
    'delete': 'Peut supprimer',
    'view': 'Peut consulter',
}

_CUSTOM_PERMISSION_NAMES = {
    ('api', 'parishdocument', 'approve_parishdocument'):
        'Peut valider et archiver les documents paroissiaux',
    ('api', 'parishdocument', 'view_sensitive_parishdocument'):
        'Peut consulter les documents paroissiaux confidentiels',
}


def translate_admin_permission_names(app_registry=None, using='default'):
    if app_registry is None:
        from django.apps import apps as app_registry

    Permission = app_registry.get_model('auth', 'Permission')
    manager = Permission.objects.using(using)

    for (app_label, model_name), object_label in _PERMISSION_OBJECTS.items():
        for action, action_label in _ACTIONS.items():
            manager.filter(
                content_type__app_label=app_label,
                content_type__model=model_name,
                codename=f'{action}_{model_name}',
            ).update(name=f'{action_label} {object_label}')

    for (app_label, model_name, codename), permission_name in _CUSTOM_PERMISSION_NAMES.items():
        manager.filter(
            content_type__app_label=app_label,
            content_type__model=model_name,
            codename=codename,
        ).update(name=permission_name)

    manager.filter(
        content_type__app_label='api',
        codename='add_parishdocumenttemplate',
    ).update(name='Peut ajouter un modèle de document paroissial')
    manager.filter(
        content_type__app_label='api',
        codename='change_parishdocumenttemplate',
    ).update(name='Peut modifier un modèle de document paroissial')
    manager.filter(
        content_type__app_label='api',
        codename='view_parishdocumenttemplate',
    ).update(name='Peut consulter les modèles de documents paroissiaux')
