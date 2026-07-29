from statix_robot.infrastructure.selenium_statix import CredenciaisStatix, SeleniumStatix


def testar_navegacao() -> None:
    """Valida login e chegada à tela de Despesas, sem alterar dados."""
    plataforma = SeleniumStatix.do_ambiente()
    try:
        plataforma.conectar(abrir_despesas=True)
        print("[OK] Tela de Despesas aberta. Nenhuma operação financeira foi executada.")
    finally:
        plataforma.fechar()
