from django.shortcuts import redirect
from django.urls import reverse


class ForcarTrocaSenhaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    from django.shortcuts import redirect
from django.urls import reverse
from django.db.utils import OperationalError


class ForcarTrocaSenhaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            user = request.user

            if (
                user.is_authenticated
                and getattr(user, "precisa_trocar_senha", False)
                and request.path != reverse("accounts:trocar_senha")
                and not request.path.startswith("/admin/")
            ):
                return redirect("accounts:trocar_senha")

        except OperationalError:
            # Banco indisponível momentaneamente → ignora middleware
            pass

        except Exception:
            # Segurança extra (evita qualquer 500 inesperado)
            pass

        return self.get_response(request)
