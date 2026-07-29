"""Consulta histórica definida exclusivamente na configuração privada."""

from statix_robot.infrastructure.configuracao_privada import carregar_configuracao_robo
from statix_robot.infrastructure.selenium_statix import SeleniumStatix


def consultar_historico_configurado() -> None:
    dados = carregar_configuracao_robo().consulta_historico
    if not dados:
        raise ValueError("Defina robo.consulta_historico na configuração privada.")
    plataforma = SeleniumStatix.do_ambiente()
    try:
        plataforma.conectar(abrir_despesas=True)
        linhas = plataforma.consultar_linhas(dados)
        print(f"[OK] Linhas encontradas pela consulta: {len(linhas)}")
        for numero, linha in enumerate(linhas, start=1):
            print(f"[STATIX {numero}] " + " | ".join(linha))
    finally:
        plataforma.fechar()
