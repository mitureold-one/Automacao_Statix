from statix_robot.infrastructure.selenium_statix import CredenciaisStatix, SeleniumStatix


def testar_login() -> None:
    """Valida exclusivamente autenticação; não acessa dados financeiros."""
    plataforma = SeleniumStatix.do_ambiente()
    try:
        plataforma.conectar(abrir_despesas=False)
        print("[OK] Login confirmado. Nenhuma operação financeira foi executada.")
    finally:
        plataforma.fechar()
