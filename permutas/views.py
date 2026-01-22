from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.contrib import messages
from django.db.models import Q

from escalas.models import AlocacaoEscala
from .models import Permuta
from .services import validar_permuta, executar_pedido_permuta, executar_permuta_direta

@login_required
def minhas_permutas(request):
    permutas = Permuta.objects.filter(
        Q(solicitante=request.user) |
        Q(alocacao_destino__usuario=request.user)
    ).select_related(
        "alocacao_origem__turno__dia",
        "alocacao_destino__usuario",
    ).order_by("-criada_em")

    return render(
        request,
        "permutas/minhas_permutas.html",
        {"permutas": permutas},
    )

@login_required
def solicitar_permuta_direta(request, alocacao_id):
    alocacao_origem = get_object_or_404(
        AlocacaoEscala,
        id=alocacao_id,
        usuario=request.user,
    )

    if request.method == "POST":
        alocacao_destino_id = request.POST.get("alocacao_destino")

        alocacao_destino = get_object_or_404(
            AlocacaoEscala,
            id=alocacao_destino_id,
        )

        permuta = Permuta.objects.create(
            solicitante=request.user,
            tipo="DIRETA",
            alocacao_origem=alocacao_origem,
            alocacao_destino=alocacao_destino,
        )

        validar_permuta(permuta)

        return redirect("permutas:minhas_permutas")

    alocacoes_possiveis = AlocacaoEscala.objects.filter(
        turno__dia__escala=alocacao_origem.turno.dia.escala
    ).exclude(usuario=request.user)

    return render(
        request,
        "permutas/solicitar_permuta_direta.html",
        {
            "alocacao_origem": alocacao_origem,
            "alocacoes_possiveis": alocacoes_possiveis,
        },
    )

@login_required
def solicitar_pedido_permuta(request, alocacao_id):
    alocacao = get_object_or_404(
        AlocacaoEscala,
        id=alocacao_id,
        usuario=request.user,
    )

    permuta = Permuta.objects.create(
        solicitante=request.user,
        tipo="PEDIDO",
        alocacao_origem=alocacao,
    )

    validar_permuta(permuta)

    return redirect("permutas:minhas_permutas")

@login_required
def pedidos_permuta(request):
    if not request.user.pode_escalar():
        raise PermissionDenied

    permutas = Permuta.objects.filter(
        tipo="PEDIDO",
        status="PENDENTE",
        alocacao_origem__turno__dia__escala__secao=request.user.secao,
    ).select_related(
        "solicitante",
        "alocacao_origem__turno__dia",
    )

    return render(
        request,
        "permutas/pedidos_permuta.html",
        {"permutas": permutas},
    )

@login_required
def aprovar_pedido(request, permuta_id):
    if not request.user.pode_escalar():
        raise PermissionDenied

    permuta = get_object_or_404(Permuta, id=permuta_id, status="PENDENTE")
    alocacao = permuta.alocacao_origem
    turno = alocacao.turno

    if request.method == "POST":
        novo_usuario_id = request.POST.get("usuario")

        novo_usuario = get_object_or_404(
            permuta.alocacao_origem.turno.dia.escala.secao.usuarios,
            id=novo_usuario_id,
        )

        # 🚨 VALIDAÇÃO IMPORTANTE
        conflito = AlocacaoEscala.objects.filter(
            turno=turno,
            usuario=novo_usuario,
        ).exclude(id=alocacao.id).exists()

        if conflito:
            messages.error(
                request,
                f"O operador {novo_usuario.username} já está escalado neste turno."
            )
            return redirect("permutas:aprovar", permuta_id=permuta.id)

        executar_pedido_permuta(permuta, novo_usuario)

        messages.success(
            request,
            "Permuta aprovada com sucesso."
        )

        return redirect("permutas:pedidos")

    usuarios = permuta.alocacao_origem.turno.dia.escala.secao.usuarios.exclude(
        papel="ENC"
    )

    return render(
        request,
        "permutas/aprovar_pedido.html",
        {
            "permuta": permuta,
            "usuarios": usuarios,
        },
    )


@login_required
def rejeitar_pedido(request, permuta_id):
    if not request.user.pode_escalar():
        raise PermissionDenied

    permuta = get_object_or_404(Permuta, id=permuta_id, status="PENDENTE")

    permuta.status = "REJEITADA"
    permuta.resolvida_em = timezone.now()
    permuta.save()

    return redirect("permutas:pedidos")


@login_required
def permutas_recebidas(request):
    permutas = Permuta.objects.filter(
        tipo="DIRETA",
        status="PENDENTE",
        alocacao_destino__usuario=request.user,
    ).select_related(
        "alocacao_origem__turno__dia",
        "alocacao_destino__turno__dia",
    )

    return render(
        request,
        "permutas/permutas_recebidas.html",
        {"permutas": permutas},
    )

@login_required
def aceitar_permuta_direta(request, permuta_id):
    permuta = get_object_or_404(
        Permuta,
        id=permuta_id,
        tipo="DIRETA",
        status="PENDENTE",
        alocacao_destino__usuario=request.user,
    )

    executar_permuta_direta(permuta)
    return redirect("permutas:recebidas")

@login_required
def rejeitar_permuta_direta(request, permuta_id):
    permuta = get_object_or_404(
        Permuta,
        id=permuta_id,
        tipo="DIRETA",
        status="PENDENTE",
        alocacao_destino__usuario=request.user,
    )

    permuta.status = "REJEITADA"
    permuta.resolvida_em = timezone.now()
    permuta.save()

    return redirect("permutas:recebidas")
