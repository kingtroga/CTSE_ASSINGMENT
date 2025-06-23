# core/apps.py
from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        """
        This method is called when the Django app is ready.
        Uncomment the import below to enable signal registration.

        Note:
        If you're running this locally and not using signals,
        leaving it commented avoids potential import errors.
        """
        # from core import signals
        pass