import hashlib
import json
from pathlib import Path

from statix_robot.application.executor import ExecutorRobo
from statix_robot.domain.configuracao import ConfiguracaoExecucao
from statix_robot.infrastructure.planilha_homologada import carregar_planilha_homologada
from statix_robot.infrastructure.progresso import RepositorioProgresso
from statix_robot.infrastructure.selenium_statix import CredenciaisStatix, SeleniumStatix


def selecionar_item(caminho_saida: Path, criterios: dict):
    lancamentos = carregar_planilha_homologada(caminho_saida)

    def corresponde(lancamento) -> bool:
        for campo, esperado in criterios.items():
            atual = getattr(lancamento, campo, None)
            if isinstance(esperado, (int, float)):
                if float(atual) != float(esperado):
                    return False
            elif str(atual) != str(esperado):
                return False
        return True

    encontrados = [lancamento for lancamento in lancamentos if corresponde(lancamento)]
    if len(encontrados) != 1:
        raise ValueError(f"A seleção deve retornar exatamente um lançamento; encontrados: {len(encontrados)}.")
    return encontrados[0]


def caminho_progresso_do_item(caminho_base: Path, item) -> Path:
    """Evita que a posicao 0 de um teste anterior pule outro item unitario."""
    identidade = {
        campo: getattr(item, campo)
        for campo in ("LOJA", "FORNECEDOR", "DATA_EMISSAO", "DATA_VENCIMENTO", "VALOR")
    }
    serializado = json.dumps(identidade, ensure_ascii=False, sort_keys=True, default=str)
    sufixo = hashlib.sha256(serializado.encode("utf-8")).hexdigest()[:12]
    return caminho_base.with_name(f"{caminho_base.stem}_{sufixo}{caminho_base.suffix}")


def executar_item_real(
    caminho_saida: Path, caminho_progresso: Path, criterios: dict, aceitar_pagamento_mais_um_dia: bool = False,
) -> dict:
    item = selecionar_item(caminho_saida, criterios)
    plataforma = SeleniumStatix.do_ambiente()
    executor = ExecutorRobo(
        plataforma,
        RepositorioProgresso(caminho_progresso_do_item(caminho_progresso, item)),
        ConfiguracaoExecucao(simulacao=False, aceitar_pagamento_mais_um_dia=aceitar_pagamento_mais_um_dia),
    )
    try:
        plataforma.conectar()
        return executor.executar([item])
    finally:
        plataforma.fechar()
