import tempfile
import unittest
from pathlib import Path

from statix_processor.domain.lancamento_saida import Lancamento_Saida
from statix_robot.application.executor import ExecutorRobo
from statix_robot.domain.configuracao import ConfiguracaoExecucao
from statix_robot.domain.plataforma import StatusPlataforma
from statix_robot.infrastructure.progresso import RepositorioProgresso


def lancamento():
    return Lancamento_Saida(
        LOJA="LOJA EXEMPLO", FORNECEDOR="FORNECEDOR TESTE", PLANO_CONTAS="0.0 - CATEGORIA EXEMPLO",
        DESCRICAO="TESTE", BANCO="BANCO EXEMPLO", DATA_VENCIMENTO="02/06/2026", DATA_EMISSAO="01/06/2026",
        DATA_PAGAMENTO="02/06/2026", VALOR=100.0,
    )


class PlataformaFalsa:
    def __init__(self, status):
        self.status = status
        self.acoes = []

    def verificar(self, dados):
        self.acoes.append("verificar")
        return self.status

    def lancar(self, dados):
        self.acoes.append("lancar")

    def pagar(self, dados):
        self.acoes.append("pagar")


class RoboTestCase(unittest.TestCase):
    def executar(self, plataforma):
        diretorio = tempfile.TemporaryDirectory()
        self.addCleanup(diretorio.cleanup)
        progresso = Path(diretorio.name) / "progresso.json"
        executor = ExecutorRobo(plataforma, RepositorioProgresso(progresso), ConfiguracaoExecucao(simulacao=True))
        return executor, progresso

    def test_simulacao_lanca_e_paga_sem_gravar_progresso(self):
        plataforma = PlataformaFalsa(StatusPlataforma.NAO_ENCONTRADO)
        executor, progresso = self.executar(plataforma)
        resumo = executor.executar([lancamento()])
        self.assertEqual(["verificar", "lancar", "pagar"], plataforma.acoes)
        self.assertEqual(1, resumo["simulados"])
        self.assertFalse(progresso.exists())

    def test_pendente_pula_lancamento_e_simula_pagamento(self):
        plataforma = PlataformaFalsa(StatusPlataforma.PENDENTE)
        executor, _ = self.executar(plataforma)
        executor.executar([lancamento()])
        self.assertEqual(["verificar", "pagar"], plataforma.acoes)

    def test_duplicata_interrompe_o_lote(self):
        plataforma = PlataformaFalsa(StatusPlataforma.DUPLICATA)
        executor, _ = self.executar(plataforma)
        with self.assertRaisesRegex(RuntimeError, "Duplicata detectada"):
            executor.executar([lancamento()])
        self.assertEqual(["verificar"], plataforma.acoes)


if __name__ == "__main__":
    unittest.main()
