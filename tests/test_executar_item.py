import tempfile
import unittest
from pathlib import Path

import pandas as pd

from statix_robot.application.executar_item import caminho_progresso_do_item, selecionar_item


class ExecutarItemTestCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.arquivo = Path(self.temp.name) / "saida.xlsx"
        pd.DataFrame([{
            "LOJA": "LOJA EXEMPLO", "FORNECEDOR": "ÓRGÃO EXEMPLO", "PLANO_CONTAS": "0.2 - TRIBUTOS",
            "DESCRICAO": "GUIA DE TRIBUTO EXEMPLO", "BANCO": "BANCO EXEMPLO", "DATA_VENCIMENTO": "16/06/2026",
            "DATA_EMISSAO": "16/06/2026", "DATA_PAGAMENTO": "19/06/2026", "VALOR": 155.68,
            "VALOR_JUROS": 0.0, "VALOR_DESCONTO": 0.0,
        }]).to_excel(self.arquivo, index=False)

    def test_seleciona_um_unico_lancamento(self):
        item = selecionar_item(self.arquivo, {"FORNECEDOR": "ÓRGÃO EXEMPLO", "VALOR": 155.68})
        self.assertEqual("GUIA DE TRIBUTO EXEMPLO", item.DESCRICAO)

    def test_rejeita_criterio_sem_correspondencia(self):
        with self.assertRaisesRegex(ValueError, "encontrados: 0"):
            selecionar_item(self.arquivo, {"VALOR": 999.0})

    def test_progresso_unitario_e_especifico_do_lancamento(self):
        item = selecionar_item(self.arquivo, {"VALOR": 155.68})
        caminho = caminho_progresso_do_item(Path("progresso_robo_item.json"), item)
        self.assertRegex(caminho.name, r"^progresso_robo_item_[0-9a-f]{12}\.json$")


if __name__ == "__main__":
    unittest.main()
