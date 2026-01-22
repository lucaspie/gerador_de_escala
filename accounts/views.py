from datetime import date
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from django.contrib.auth import authenticate, login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from django.views.generic import TemplateView
from .forms import CriarUsuarioForm, EditarUsuarioForm
from django.contrib import messages
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user = self.request.user

        if user.papel == "OPE":
            context["mensagem"] = "Bem-vindo! Aqui você pode acompanhar suas escalas e solicitar permutas."
        elif user.papel == "ESC":
            context["mensagem"] = "Bem-vindo! Aqui você pode criar e gerenciar escalas."
        else:  # ENC
            context["mensagem"] = "Bem-vindo! Aqui você pode acompanhar as escalas do projeto."

        return context

@login_required
def minhas_escalas(request):
    alocacoes = request.user.alocacoes.select_related(
        "turno__dia__escala"
    ).order_by("turno__dia__data")

    return render(
        request,
        "accounts/minhas_escalas.html",
        {"alocacoes": alocacoes},
    )

@login_required
def dashboard(request):
    user = request.user

    if user.papel == "OPE":
        mensagem = "Bem-vindo! Aqui estão suas escalas."
    else:
        mensagem = "Bem-vindo! Gerencie as escalas da sua seção."

    return render(
        request,
        "accounts/dashboard.html",
        {"mensagem": mensagem},
    )

User = get_user_model()

@login_required
def cadastrar_usuario(request):
    if not request.user.pode_escalar():
        messages.error(request, "Você não tem permissão.")
        return redirect("home")

    if request.method == "POST":
        form = CriarUsuarioForm(request.POST)
        if form.is_valid():
            usuario = form.save(commit=False)

            usuario.set_password("SenhaPadrao")
            usuario.precisa_trocar_senha = True
            usuario.save()
            form.save_m2m()

            messages.success(
                request,
                f"Usuário criado com sucesso. Senha inicial: SenhaPadrao"
            )
            return redirect("accounts:dashboard")
    else:
        form = CriarUsuarioForm()

    return render(request, "accounts/cadastrar_usuario.html", {"form": form})

class TrocarSenhaObrigatoriaView(PasswordChangeView):
    template_name = "accounts/trocar_senha.html"
    success_url = reverse_lazy("accounts:dashboard")

    def form_valid(self, form):
        response = super().form_valid(form)
        self.request.user.precisa_trocar_senha = False
        self.request.user.save()
        return response
    
@login_required
def editar_usuario(request, user_id):
    if not request.user.pode_escalar():
        messages.error(request, "Você não tem permissão.")
        return redirect("home")

    usuario = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        form = EditarUsuarioForm(request.POST, instance=usuario)
        if form.is_valid():
            usuario = form.save(commit=False)

            if form.cleaned_data.get("forcar_troca_senha"):
                usuario.precisa_trocar_senha = True

            usuario.save()
            form.save_m2m()

            messages.success(request, "Usuário atualizado com sucesso.")
            return redirect("accounts:lista_usuarios")
    else:
        form = EditarUsuarioForm(instance=usuario)

    return render(
        request,
        "accounts/editar_usuario.html",
        {
            "form": form,
            "usuario": usuario,
        },
    )

@login_required
def lista_usuarios(request):
    if not request.user.pode_escalar():
        messages.error(request, "Você não tem permissão para acessar esta página.")
        return redirect("home")

    usuarios = (
        User.objects
        .select_related("secao")
        .prefetch_related("cursos")
        .order_by("secao__nome", "papel", "username")
    )

    return render(
        request,
        "accounts/lista_usuarios.html",
        {
            "usuarios": usuarios,
        },
    )

@login_required
def resetar_senha_usuario(request, user_id):
    if not request.user.pode_escalar():
        messages.error(request, "Sem permissão.")
        return redirect("accounts:lista_usuarios")

    usuario = get_object_or_404(User, id=user_id)

    usuario.set_password("SenhaPadrao")
    usuario.precisa_trocar_senha = True
    usuario.save()

    messages.success(
        request,
        f"Senha de {usuario.username} resetada para 'SenhaPadrao'."
    )

    return redirect("accounts:lista_usuarios")