from pathlib import Path

import pandas as pd

from statix_processor.domain.contrato import COLUNAS_HOMOLOGADAS, validar_lancamentos_operacionais
from statix_processor.domain.lancamento_saida import Lancamento_Saida


def carregar_planilha_homologada(caminho: Path) -> list[Lancamento_Saida]:
    if not caminho.exists():
        raise FileNotFoundError(f"Saída homologada não encontrada: {caminho.resolve()}")
    dados = pd.read_excel(caminho)
    faltantes = [coluna for coluna in COLUNAS_HOMOLOGADAS if coluna not in dados.columns]
    if faltantes:
        raise ValueError(f"Planilha não atende ao contrato; colunas ausentes: {', '.join(faltantes)}")

    lancamentos = [Lancamento_Saida(**linha) for linha in dados[list(COLUNAS_HOMOLOGADAS)].to_dict("records")]
    erros = validar_lancamentos_operacionais(list(enumerate(lancamentos, start=2)))
    if erros:
        raise ValueError("Planilha não atende ao contrato:\n" + "\n".join(erros))
    return lancamentos
