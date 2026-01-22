from django.shortcuts import redirect
from django.urls import reverse


class ForcarTrocaSenhaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.user.is_authenticated
            and request.user.precisa_trocar_senha
            and request.path != reverse("accounts:trocar_senha")
            and not request.path.startswith("/admin/")
        ):
            return redirect("accounts:trocar_senha")

        return self.get_response(request)
