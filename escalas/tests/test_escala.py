import pytest
from datetime import date, timedelta
from collections import Counter

from accounts.models import User, CursoOperacional, Curso
from escalas.models import Escala
from projetos.models import Projeto, Secao
from escalas.services import gerar_escala_semanal, encerrar_escala, criar_sobreaviso_service

# =========================
# FIXTURES
# =========================

@pytest.fixture
def secao(db):
    projeto = Projeto.objects.create(nome="Projeto Teste")
    return Secao.objects.create(nome="A", projeto=projeto)

@pytest.fixture
def curso_man(db):
    return CursoOperacional.objects.get_or_create(codigo=Curso.MANUTENCAO)[0]

@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        username="admin", 
        password="123", 
        papel=User.Papel.ENCARREGADO, 
        is_staff=True
    )

@pytest.fixture
def criar_operadores(db, secao, curso_man):
    """Helper para criar múltiplos operadores com curso."""
    def _criar(qtd, prefixo="op"):
        ops = []
        for i in range(qtd):
            u = User.objects.create_user(
                username=f"{prefixo}{i}",
                password="123",
                secao=secao,
                papel=User.Papel.OPERADOR
            )
            u.cursos.add(curso_man)
            ops.append(u)
        return ops
    return _criar

# =========================
# TESTES DE GERAÇÃO
# =========================
    
@pytest.mark.django_db
def test_simulacao_6_meses_fairness(secao, admin_user, criar_operadores):
    """
    Simula 6 meses de escalas para validar estabilidade de fairness no longo prazo.
    """

    from collections import Counter
    from datetime import date, timedelta

    criar_operadores(15)  # número realista

    contagem = Counter()
    data_base = date(2026, 1, 5)

    semanas = 26  # ~6 meses

    for _ in range(semanas):
        escala = gerar_escala_semanal(
            secao=secao,
            data_inicio=data_base,
            criada_por=admin_user,
            qtd_madrugada=0,
            qtd_noturno=2,
            modo="DIN"
        )

        # IMPORTANTÍSSIMO (mantém histórico válido)
        escala.status = Escala.Status.PUBLICADA
        escala.save()

        for dia in escala.dias.all():
            for turno in dia.turnos.all():
                for aloc in turno.alocacoes.filter(tipo="TIT"):
                    contagem[aloc.usuario.username] += 1

        data_base += timedelta(days=7)

    valores = list(contagem.values())
    diff = max(valores) - min(valores)

    print("\nDistribuição 6 meses:")
    print(dict(contagem))
    print(f"Diff final: {diff}")

    # tolerância mais flexível (escala longa)
    assert diff <= 3
    
@pytest.mark.django_db
def test_mesmos_operadores_todos_os_dias(secao, admin_user, criar_operadores):
    criar_operadores(10)

    from datetime import date

    escala = gerar_escala_semanal(
        secao=secao,
        data_inicio=date(2026, 1, 5),
        criada_por=admin_user,
        qtd_madrugada=0,
        qtd_noturno=2,
        modo="SEM"
    )

    operadores_por_dia = []

    for dia in escala.dias.all():
        if dia.tipo_dia == "VERMELHA":
            continue

        ops_dia = set()

        for turno in dia.turnos.all():
            for aloc in turno.alocacoes.filter(tipo="TIT"):
                ops_dia.add(aloc.usuario_id)

        operadores_por_dia.append(ops_dia)

    # pega o primeiro dia como base
    base = operadores_por_dia[0]

    for i, ops in enumerate(operadores_por_dia[1:], start=1):
        assert ops == base, f"Dia {i} diferente: {ops} != {base}"
        
        
@pytest.mark.django_db
def test_substituicao_por_indisponibilidade(secao, admin_user, criar_operadores):
    ops = criar_operadores(5)

    from datetime import date
    from indisponibilidades.models import Indisponibilidade

    # deixa um operador indisponível no meio da semana
    Indisponibilidade.objects.create(
        usuario=ops[0],
        data_inicio=date(2026, 1, 7),
        data_fim=date(2026, 1, 7),
    )

    escala = gerar_escala_semanal(
        secao=secao,
        data_inicio=date(2026, 1, 5),
        criada_por=admin_user,
        qtd_madrugada=0,
        qtd_noturno=2,
        modo="SEM"
    )

    operadores_por_dia = []

    for dia in escala.dias.all():
        if dia.tipo_dia == "VERMELHA":
            continue

        ops_dia = set(
            aloc.usuario_id
            for turno in dia.turnos.all()
            for aloc in turno.alocacoes.filter(tipo="TIT")
        )

        operadores_por_dia.append((dia.data, ops_dia))

    for data, ops_dia in operadores_por_dia:
        if data == date(2026, 1, 7):
            # pode ser diferente nesse dia
            continue

        assert ops_dia == operadores_por_dia[0][1]