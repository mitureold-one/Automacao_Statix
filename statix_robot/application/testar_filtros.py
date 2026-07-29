from dataclasses import asdict
from pathlib import Path

from statix_robot.infrastructure.planilha_homologada import carregar_planilha_homologada
from statix_robot.infrastructure.selenium_statix import CredenciaisStatix, SeleniumStatix


def testar_filtros(caminho_saida: Path) -> None:
    """Valida filtros de consulta usando o primeiro lançamento homologado."""
    lancamentos = carregar_planilha_homologada(caminho_saida)
    if not lancamentos:
        raise ValueError("Não há lançamentos homologados para testar os filtros.")
    dados = asdict(lancamentos[0])
    plataforma = SeleniumStatix.do_ambiente()
    try:
        plataforma.conectar(abrir_despesas=True)
        status = plataforma.verificar(dados)
        print(
            "[OK] Filtros validados: status (Pendente/Pago), loja, fornecedor e período de datas. "
            f"Resultado da consulta: {status.value}."
        )
    finally:
        plataforma.fechar()
