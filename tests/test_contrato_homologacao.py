import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from statix_processor.domain.contrato import COLUNAS_HOMOLOGADAS, validar_lancamentos_operacionais
from statix_processor.domain.lancamento_saida import Lancamento_Saida
from statix_processor.infrastructure.historico import registrar_execucao


def lancamento(**alteracoes):
    dados = {
        "LOJA": "LOJA EXEMPLO",
        "FORNECEDOR": "FORNECEDOR TESTE",
        "PLANO_CONTAS": "7.1 - FUNDO DE LOJA",
        "DESCRICAO": "TESTE",
        "BANCO": "BANCO EXEMPLO",
        "DATA_VENCIMENTO": "02/06/2026",
        "DATA_EMISSAO": "01/06/2026",
        "DATA_PAGAMENTO": "02/06/2026",
        "VALOR": 100.0,
        "VALOR_JUROS": 0.0,
        "VALOR_DESCONTO": 0.0,
    }
    dados.update(alteracoes)
    return Lancamento_Saida(**dados)


class ContratoHomologacaoTestCase(unittest.TestCase):
    def test_contrato_lista_todas_as_colunas_exportadas(self):
        self.assertEqual(11, len(COLUNAS_HOMOLOGADAS))

    def test_lancamento_valido_atende_contrato(self):
        self.assertEqual([], validar_lancamentos_operacionais([(2, lancamento())]))

    def test_contrato_rejeita_data_invalida_e_valor_negativo(self):
        erros = validar_lancamentos_operacionais([
            (7, lancamento(DATA_EMISSAO="2026-06-03", VALOR=-1)),
        ])
        self.assertTrue(any("DATA_EMISSAO" in erro for erro in erros))
        self.assertTrue(any("VALOR" in erro for erro in erros))

    def test_historico_guarda_assinatura_da_entrada(self):
        with tempfile.TemporaryDirectory() as diretorio:
            raiz = Path(diretorio)
            entrada = raiz / "entrada.xlsx"
            historico = raiz / "historico.jsonl"
            entrada.write_bytes(b"conteudo de teste")
            with patch("statix_processor.infrastructure.historico.ARQUIVO_HISTORICO", historico):
                registrar_execucao(
                    entrada=entrada,
                    status="HOMOLOGADO",
                    transformados=1,
                    aprovados=1,
                    fora_exportacao=0,
                    erros=0,
                    avisos=[],
                    bloqueios=[],
                    arquivo_saida="saida.xlsx",
                )
            registro = historico.read_text(encoding="utf-8")
            self.assertIn('"status": "HOMOLOGADO"', registro)
            self.assertIn('"sha256_entrada"', registro)


if __name__ == "__main__":
    unittest.main()
