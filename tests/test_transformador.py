import unittest
from datetime import datetime
from pathlib import Path

from statix_processor.domain.lancamento_entrada import Lancamento_Entrada
from statix_processor.infrastructure.configuracao_negocio import carregar_configuracao
from statix_processor.services.transformacao import Transformador


class TransformadorTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        exemplo = Path(__file__).parents[1] / "config" / "negocio.example.json"
        cls.transformador = Transformador(carregar_configuracao(exemplo))

    def entrada(self, loja="LOJA_EXEMPLO", nf="", origem="FORNECEDOR_EXEMPLO", juros=0.0):
        return Lancamento_Entrada(
            LOJA=loja,
            NF=nf,
            VALOR=200.0,
            ORIGEM=origem,
            DATA_VENCIMENTO=datetime(2026, 6, 2),
            MES_REFERENCIA="2026-06",
            DATA_PAGAMENTO=datetime(2026, 6, 2),
            BANCO="BANCO DA ENTRADA",
            JUROS=juros,
        )

    def test_excecao_de_fornecedor_por_loja_e_nf(self):
        saida = self.transformador.transformar(self.entrada(nf="DESCRIÇÃO ESPECIAL"))
        self.assertEqual("FORNECEDOR ESPECIAL EXEMPLO", saida.FORNECEDOR)

    def test_regra_nf_sobrescreve_fornecedor_e_plano(self):
        saida = self.transformador.transformar(self.entrada(nf="GUIA TRIBUTO_EXEMPLO"))
        self.assertEqual("ÓRGÃO PÚBLICO EXEMPLO", saida.FORNECEDOR)
        self.assertEqual("0.2 - TRIBUTOS", saida.PLANO_CONTAS)

    def test_emissao_usa_prazo_do_fornecedor(self):
        saida = self.transformador.transformar(self.entrada())
        self.assertEqual("03/05/2026", saida.DATA_EMISSAO)

    def test_juros_negativo_vira_desconto(self):
        saida = self.transformador.transformar(self.entrada(juros=-12.5))
        self.assertEqual(0.0, saida.VALOR_JUROS)
        self.assertEqual(12.5, saida.VALOR_DESCONTO)

    def test_cadastros_desconhecidos_sao_sinalizados(self):
        saida = self.transformador.transformar(
            self.entrada(loja="LOJA_NOVA", origem="FORNECEDOR_NOVO")
        )
        self.assertIn("Desconhecida", saida.LOJA)
        self.assertIn("Desconhecido", saida.FORNECEDOR)
        self.assertIn("Desconhecido", saida.PLANO_CONTAS)
        self.assertIn("Desconhecido", saida.BANCO)

    def test_nf_numerica_nao_substitui_descricao(self):
        saida = self.transformador.transformar(self.entrada(nf="123456"))
        self.assertEqual("COMPRA EXEMPLO", saida.DESCRICAO)


if __name__ == "__main__":
    unittest.main()
