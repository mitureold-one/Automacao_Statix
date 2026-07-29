from pathlib import Path

from statix_robot.application.executor import ExecutorRobo
from statix_robot.domain.configuracao import ConfiguracaoExecucao
from statix_robot.infrastructure.planilha_homologada import carregar_planilha_homologada
from statix_robot.infrastructure.progresso import RepositorioProgresso
from statix_robot.infrastructure.selenium_statix import CredenciaisStatix, SeleniumStatix


def executar_real(
    caminho_saida: Path, caminho_progresso: Path, somente_pagamento: bool = False, iniciar_da_linha: int = 0,
    aceitar_pagamento_mais_um_dia: bool = False,
) -> dict:
    """Executa alterações reais; chame somente após uma simulação aprovada."""
    lancamentos = carregar_planilha_homologada(caminho_saida)
    plataforma = SeleniumStatix.do_ambiente()
    executor = ExecutorRobo(
        plataforma,
        RepositorioProgresso(caminho_progresso),
        ConfiguracaoExecucao(
            somente_pagamento=somente_pagamento,
            iniciar_da_linha=iniciar_da_linha,
            simulacao=False,
            aceitar_pagamento_mais_um_dia=aceitar_pagamento_mais_um_dia,
        ),
    )
    try:
        plataforma.conectar()
        return executor.executar(lancamentos)
    finally:
        plataforma.fechar()
