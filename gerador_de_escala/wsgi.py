"""
WSGI config for gerador_de_escala project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gerador_de_escala.settings')

application = get_wsgi_application()

import time
from django.db import connection

def wait_for_db():
    for _ in range(5):
        try:
            connection.ensure_connection()
            return
        except Exception:
            time.sleep(2)
