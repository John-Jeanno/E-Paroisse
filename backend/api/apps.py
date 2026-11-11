from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.utils.translation import gettext_lazy as _

class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'
    verbose_name = _('Gestion paroissiale')

    def ready(self):
        from .admin_localization import translate_admin_permission_names

        post_migrate.connect(
            self._translate_permission_names,
            sender=self,
            dispatch_uid='api.translate_admin_permission_names',
        )
        # Import signals to register post_save handlers
        try:
            from . import signals  # noqa: F401
        except Exception:
            # Avoid raising on import errors during migrations or tests
            pass

    def _translate_permission_names(self, using, **kwargs):
        from .admin_localization import translate_admin_permission_names

        translate_admin_permission_names(using=using)
