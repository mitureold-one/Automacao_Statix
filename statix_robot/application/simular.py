from pathlib import Path

from statix_robot.application.executor import ExecutorRobo
from statix_robot.domain.configuracao import ConfiguracaoExecucao
from statix_robot.infrastructure.planilha_homologada import carregar_planilha_homologada
from statix_robot.infrastructure.progresso import RepositorioProgresso
from statix_robot.infrastructure.simulador import SimuladorPlataforma


def simular(caminho_saida: Path, caminho_progresso: Path) -> dict:
    lancamentos = carregar_planilha_homologada(caminho_saida)
    executor = ExecutorRobo(
        SimuladorPlataforma(),
        RepositorioProgresso(caminho_progresso),
        ConfiguracaoExecucao(simulacao=True),
    )
    return executor.executar(lancamentos)
