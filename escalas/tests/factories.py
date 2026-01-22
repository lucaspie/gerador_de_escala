from django.contrib.auth import get_user_model
from projetos.models import Secao, Projeto

User = get_user_model()


def criar_projeto(nome="Projeto Teste"):
    return Projeto.objects.create(
        nome=nome,
        descricao="Projeto criado para testes",
        ativo=True,
    )


def criar_secao(nome="GUARNAE", projeto=None):
    if projeto is None:
        projeto = criar_projeto()

    return Secao.objects.create(
        nome=nome,
        projeto=projeto,
        ativa=True,
    )


def criar_operador(secao, username):
    return User.objects.create_user(
        username=username,
        password="123",
        secao=secao,
        papel="OPE",
    )
