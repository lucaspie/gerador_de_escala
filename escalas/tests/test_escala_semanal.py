from datetime import date
from django.test import TestCase
from escalas.services import gerar_escala_semanal
from escalas.models import AlocacaoEscala
from .factories import criar_secao, criar_operador


class TestGerarEscalaSemanal(TestCase):

    def setUp(self):
        self.secao = criar_secao()
        self.operadores = [
            criar_operador(self.secao, f"op{i}")
            for i in range(6)
        ]

    def test_todos_operadores_sao_utilizados(self):
        escala = gerar_escala_semanal(
            secao=self.secao,
            data_inicio=date(2025, 1, 6),  # segunda
            criada_por=self.operadores[0],
            qtd_madrugada=1,
            qtd_noturno=1,
        )

        usuarios_escalados = (
            AlocacaoEscala.objects
            .filter(turno__dia__escala=escala)
            .values_list("usuario_id", flat=True)
            .distinct()
        )

        self.assertEqual(
            set(usuarios_escalados),
            set(op.id for op in self.operadores)
        )
