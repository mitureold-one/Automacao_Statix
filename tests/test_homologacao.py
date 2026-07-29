import unittest

from pathlib import Path

import statix_processor.application.pipeline as pipeline
from statix_processor.domain.lancamento_saida import Lancamento_Saida
from statix_processor.infrastructure.configuracao_negocio import carregar_configuracao


def lancamento(loja="Loja Exemplo", fornecedor="FORNECEDOR", plano="0.0 - CATEGORIA EXEMPLO"):
    return Lancamento_Saida(
        LOJA=loja,
        FORNECEDOR=fornecedor,
        PLANO_CONTAS=plano,
        DESCRICAO="TESTE",
        BANCO="BANCO EXEMPLO",
        DATA_VENCIMENTO="02/06/2026",
        DATA_EMISSAO="02/06/2026",
        DATA_PAGAMENTO="02/06/2026",
        VALOR=100.0,
    )


class HomologacaoTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        exemplo = Path(__file__).parents[1] / "config" / "negocio.example.json"
        pipeline.CONFIGURACAO_NEGOCIO = carregar_configuracao(exemplo)

    def test_lancamento_completo_e_aprovado(self):
        self.assertEqual(("APROVADO", ""), pipeline._status(lancamento()))

    def test_pendencia_de_cadastro_bloqueia_lancamento_operacional(self):
        status, alerta = pipeline._status(lancamento(fornecedor="Fornecedor Desconhecido! Cadastre !"))
        self.assertEqual("PENDENTE_CADASTRO", status)
        self.assertIn("FORNECEDOR", alerta)

    def test_loja_excluida_fica_no_preview_sem_bloquear_operacao(self):
        status, alerta = pipeline._status(
            lancamento(
                loja="Loja Excluída Exemplo",
                fornecedor="Fornecedor Desconhecido! Cadastre !",
                plano="Plano de Contas Desconhecido! Cadastre !",
            )
        )
        self.assertEqual("FORA_DA_EXPORTACAO", status)
        self.assertIn("cadastro pendente", alerta)


if __name__ == "__main__":
    unittest.main()
