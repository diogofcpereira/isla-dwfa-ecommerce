"""Testes (pytest-django) · tests."""

from .base import *  # noqa: F403

DEBUG = False

# Hasher rápido: os testes não medem a força das passwords · fast hasher: tests do not
# benchmark password strength
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Ficha 05 · sem Redis nos testes (nem no CI): as tarefas correm ali mesmo ("eager"),
# os resultados ficam em memória e a cache é local ao processo.
CELERY_TASK_ALWAYS_EAGER = True  # .delay() corre a função já, no processo do teste
CELERY_TASK_EAGER_PROPAGATES = True  # uma exceção na tarefa rebenta o teste
CELERY_TASK_STORE_EAGER_RESULT = True  # o AsyncResult(id) encontra o resultado
CELERY_RESULT_BACKEND = "cache+memory://"
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
REPORT_STEP_SECONDS = 0
