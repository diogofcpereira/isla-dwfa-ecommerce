# Carrega a app Celery quando o Django arranca, para o @shared_task das apps a usar
# (é assim que o .delay() da view sabe para que broker enviar).
from .celery import app as celery_app

__all__ = ("celery_app",)
