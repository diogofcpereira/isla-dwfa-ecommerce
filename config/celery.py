"""A app Celery do projeto (Ficha 05).

O worker é este mesmo projeto Django, arrancado com outro comando:
    uv run celery -A config worker -l info
"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("config")
# Lê dos settings do Django tudo o que começa por CELERY_ (CELERY_BROKER_URL → broker_url).
app.config_from_object("django.conf:settings", namespace="CELERY")
# Procura um tasks.py em cada app de INSTALLED_APPS (shop/tasks.py).
app.autodiscover_tasks()
