from datetime import date
from django.test import TestCase
from escalas.services import criar_sobreaviso_service
from escalas.models import AlocacaoEscala
from .factories import criar_secao, criar_operador


class TestSobreaviso(TestCase):

    def setUp(self):
        self.secao = criar_secao()
        self.operadores = [
            criar_operador(self.secao, f"op{i}")
            for i in range(5)
        ]

    def test_sobreaviso_nao_repete_sempre_os_mesmos(self):
        escala1 = criar_sobreaviso_service(
            secao=self.secao,
            data=date(2025, 1, 11),
            quantidade=3,
            criada_por=self.operadores[0],
        )

        escala2 = criar_sobreaviso_service(
            secao=self.secao,
            data=date(2025, 1, 18),
            quantidade=3,
            criada_por=self.operadores[0],
        )

        usuarios1 = set(
            AlocacaoEscala.objects
            .filter(turno__dia__escala=escala1)
            .values_list("usuario_id", flat=True)
        )

        usuarios2 = set(
            AlocacaoEscala.objects
            .filter(turno__dia__escala=escala2)
            .values_list("usuario_id", flat=True)
        )

        self.assertNotEqual(usuarios1, usuarios2)
