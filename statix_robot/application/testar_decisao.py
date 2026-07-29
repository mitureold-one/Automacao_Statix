from dataclasses import asdict
from pathlib import Path

from statix_robot.domain.plataforma import StatusPlataforma
from statix_robot.infrastructure.planilha_homologada import carregar_planilha_homologada
from statix_robot.infrastructure.selenium_statix import CredenciaisStatix, SeleniumStatix


def _acao_para(status: StatusPlataforma) -> str:
    return {
        StatusPlataforma.NAO_ENCONTRADO: "cadastrar e, em seguida, pagar",
        StatusPlataforma.PENDENTE: "pular cadastro e pagar",
        StatusPlataforma.PAGO: "pular cadastro e pagamento",
        StatusPlataforma.DUPLICATA: "parar para intervenção manual",
    }[status]


def testar_decisao(caminho_saida: Path) -> None:
    """Consulta os dois ramos principais sem criar ou pagar qualquer despesa."""
    lancamentos = carregar_planilha_homologada(caminho_saida)
    if not lancamentos:
        raise ValueError("Não há lançamentos homologados para testar a decisão.")
    existente = asdict(lancamentos[0])
    inexistente = {**existente, "VALOR": 999_999_999.99}
    plataforma = SeleniumStatix.do_ambiente()
    try:
        plataforma.conectar(abrir_despesas=True)
        status_existente = plataforma.verificar(existente)
        status_inexistente = plataforma.verificar(inexistente)
        print(f"[OK] Consulta existente: {status_existente.value} -> {_acao_para(status_existente)}.")
        print(f"[OK] Consulta inexistente: {status_inexistente.value} -> {_acao_para(status_inexistente)}.")
        print("[OK] Teste apenas de decisão; nenhuma despesa foi criada ou paga.")
    finally:
        plataforma.fechar()
