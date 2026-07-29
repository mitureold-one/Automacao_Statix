"""Entrada do robô; simulação é padrão e execução real exige confirmação."""

import argparse
import base64
import json
from pathlib import Path

from statix_robot.application.simular import simular


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--executar", action="store_true", help="Executa ações reais no Statix.")
    parser.add_argument("--executar-item", action="store_true", help="Executa somente o lançamento definido em --criterios-json.")
    parser.add_argument("--testar-login", action="store_true", help="Testa somente autenticação e fecha o navegador.")
    parser.add_argument("--testar-navegacao", action="store_true", help="Testa a chegada à tela de Despesas sem alterar dados.")
    parser.add_argument("--testar-filtros", action="store_true", help="Testa filtros de consulta sem alterar dados.")
    parser.add_argument("--testar-decisao", action="store_true", help="Testa os ramos de cadastro/pagamento sem alterar dados.")
    parser.add_argument("--inspecionar-api", action="store_true", help="Lista rotas de consulta usadas pela tela, sem alterar dados.")
    parser.add_argument("--consultar-historico", action="store_true", help="Executa a consulta histórica privada, sem alterar dados.")
    parser.add_argument("--auditar", action="store_true", help="Executa a auditoria definida na configuração privada.")
    parser.add_argument("--prever-estorno", type=int, help="Exibe a previa de um estorno auditado pelo ID Statix, sem alterar dados.")
    parser.add_argument("--estornar-item", type=int, help="Estorna um unico item auditado pelo ID Statix.")
    parser.add_argument("--corrigir-lote", help="IDs Statix separados por virgula para estorno e relancamento sequenciais.")
    parser.add_argument("--confirmar-estorno", action="store_true", help="Confirma o estorno unitario apos revisar a previa.")
    parser.add_argument("--confirmar-lote-correcao", action="store_true", help="Confirma o lote de correcoes apos revisar a previa.")
    parser.add_argument("--confirmar-execucao", action="store_true", help="Confirma que a simulação já foi revisada.")
    parser.add_argument("--aceitar-pagamento-mais-um-dia", action="store_true", help="Aceita explicitamente pagamento gravado um dia depois pelo Statix.")
    parser.add_argument("--somente-pagamento", action="store_true")
    parser.add_argument("--iniciar-da-linha", type=int, default=0)
    parser.add_argument("--criterios-json", help="Critérios exatos do único lançamento a executar.")
    parser.add_argument("--criterios-base64", help="Critérios exatos codificados em Base64.")
    argumentos = parser.parse_args()
    saida, progresso = Path("saida.xlsx"), Path("progresso_robo.json")

    if argumentos.testar_login:
        from statix_robot.application.testar_login import testar_login
        testar_login()
    elif argumentos.testar_navegacao:
        from statix_robot.application.testar_navegacao import testar_navegacao
        testar_navegacao()
    elif argumentos.testar_filtros:
        from statix_robot.application.testar_filtros import testar_filtros
        testar_filtros(saida)
    elif argumentos.testar_decisao:
        from statix_robot.application.testar_decisao import testar_decisao
        testar_decisao(saida)
    elif argumentos.inspecionar_api:
        from statix_robot.application.inspecionar_api import inspecionar_api
        inspecionar_api(saida)
    elif argumentos.consultar_historico:
        from statix_robot.application.consultar_historico import consultar_historico_configurado
        consultar_historico_configurado()
    elif argumentos.auditar:
        from statix_robot.application.auditar import auditar
        auditar(saida)
    elif argumentos.prever_estorno is not None:
        from statix_robot.application.estornar_item import exibir_previa_estorno
        from statix_robot.infrastructure.configuracao_privada import carregar_configuracao_robo
        exibir_previa_estorno(carregar_configuracao_robo().auditoria.arquivo, argumentos.prever_estorno)
    elif argumentos.estornar_item is not None:
        if not argumentos.confirmar_estorno:
            raise SystemExit("Estorno bloqueado: revise a previa e informe --confirmar-estorno.")
        from statix_robot.application.estornar_item import estornar_item_real
        from statix_robot.infrastructure.configuracao_privada import carregar_configuracao_robo
        estornar_item_real(carregar_configuracao_robo().auditoria.arquivo, argumentos.estornar_item)
        print("ESTORNO UNITARIO CONCLUIDO")
    elif argumentos.corrigir_lote:
        if not argumentos.confirmar_lote_correcao:
            raise SystemExit("Lote bloqueado: revise a previa e informe --confirmar-lote-correcao.")
        from statix_robot.application.corrigir_lote import executar_lote_correcao
        from statix_robot.infrastructure.configuracao_privada import carregar_configuracao_robo
        ids = [int(valor.strip()) for valor in argumentos.corrigir_lote.split(",") if valor.strip()]
        resultado = executar_lote_correcao(
            carregar_configuracao_robo().auditoria.arquivo,
            saida, ids, argumentos.aceitar_pagamento_mais_um_dia,
        )
        print(f"LOTE DE CORRECAO CONCLUIDO | IDs: {resultado['concluidos']}")
    elif argumentos.executar_item:
        criterios_serializados = argumentos.criterios_json
        if argumentos.criterios_base64:
            criterios_serializados = base64.b64decode(argumentos.criterios_base64).decode("utf-8")
        if not argumentos.confirmar_execucao or not criterios_serializados:
            raise SystemExit("Execução unitária bloqueada: informe --confirmar-execucao e um critério de seleção.")
        from statix_robot.application.executar_item import executar_item_real
        criterios = json.loads(criterios_serializados)
        resultado = executar_item_real(
            saida, Path("progresso_robo_item.json"), criterios,
            argumentos.aceitar_pagamento_mais_um_dia,
        )
        print(f"EXECUÇÃO UNITÁRIA CONCLUÍDA | concluídos: {resultado['concluidos']}")
    elif argumentos.executar:
        if not argumentos.confirmar_execucao:
            raise SystemExit("Execução real bloqueada: informe --confirmar-execucao após revisar a simulação.")
        from statix_robot.application.executar_real import executar_real
        resultado = executar_real(
            saida, progresso, argumentos.somente_pagamento, argumentos.iniciar_da_linha,
            argumentos.aceitar_pagamento_mais_um_dia,
        )
        print(f"EXECUÇÃO REAL CONCLUÍDA | concluídos: {resultado['concluidos']} | pulados: {resultado['pulados']}")
    else:
        resultado = simular(saida, progresso)
        print(f"SIMULAÇÃO CONCLUÍDA | total: {resultado['total']} | simulados: {resultado['simulados']} | pulados: {resultado['pulados']}")
