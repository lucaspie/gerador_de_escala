# core/middleware.py

from django.db.utils import OperationalError
from django.http import HttpResponse


class DatabaseRetryMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        try:
            return self.get_response(request)

        except OperationalError:
            return HttpResponse(
                "Banco iniciando, tente novamente em alguns segundos.",
                status=503
            )