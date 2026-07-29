import json
from dataclasses import asdict
from pathlib import Path

from statix_robot.infrastructure.planilha_homologada import carregar_planilha_homologada
from statix_robot.infrastructure.selenium_statix import CredenciaisStatix, SeleniumStatix


def inspecionar_api(caminho_saida: Path) -> list[dict]:
    """Descobre as rotas chamadas numa consulta real, sem mutar dados."""
    lancamentos = carregar_planilha_homologada(caminho_saida)
    if not lancamentos:
        raise ValueError("Não há lançamentos homologados para a consulta de inspeção.")
    plataforma = SeleniumStatix.do_ambiente()
    try:
        plataforma.conectar(abrir_despesas=True)
        plataforma.verificar(asdict(lancamentos[0]))
        corpo_consulta, cabecalhos = plataforma.detalhes_da_ultima_requisicao("/payables/list")
        print(f"[API] Corpo da consulta payables/list: {corpo_consulta}")
        resposta_direta = plataforma.repetir_consulta_api("/conciliador-ws/payables/list", corpo_consulta, cabecalhos)
        if "erro" in resposta_direta:
            raise RuntimeError(f"Consulta direta à API falhou: {resposta_direta['erro']}")
        print(
            "[API] Consulta direta payables/list: "
            f"HTTP {resposta_direta['status']} | resposta com {resposta_direta['tamanhoResposta']} caracteres."
        )
        try:
            resposta_json = json.loads(resposta_direta["corpo"])
            if isinstance(resposta_json, dict):
                print(f"[API] Campos da resposta: {', '.join(resposta_json.keys())}")
                listas = [valor for valor in resposta_json.values() if isinstance(valor, list)]
                if listas and listas[0] and isinstance(listas[0][0], dict):
                    print(f"[API] Campos de um lançamento: {', '.join(listas[0][0].keys())}")
        except (KeyError, TypeError, ValueError):
            print("[API] Resposta não está em JSON estruturado.")
        requisicoes = plataforma.requisicoes_api()
        for requisicao in requisicoes:
            print(f"[API] {requisicao['metodo']} {requisicao['rota']}")
        return requisicoes
    finally:
        plataforma.fechar()
