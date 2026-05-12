import os
import sys
from django.apps import AppConfig


class DepositsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'deposits'

    def ready(self):
        # Skip scheduler during management commands (migrate, test, shell, etc.)
        # In development: RUN_MAIN=true is set by Django autoreloader in the child process.
        # In production: set DJANGO_RUN_SCHEDULER=1 to opt-in explicitly.
        is_dev_child = os.environ.get('RUN_MAIN') == 'true'
        is_production = os.environ.get('DJANGO_RUN_SCHEDULER') == '1'
        if not (is_dev_child or is_production):
            return
        from . import tasks
        tasks.start_scheduler()
