"""Previa e execucao unitarias de estorno para correcoes auditadas."""

from pathlib import Path

import pandas as pd

from statix_robot.infrastructure.configuracao_privada import carregar_configuracao_robo
from statix_robot.infrastructure.selenium_statix import SeleniumStatix


def _texto_data(valor) -> str:
    return valor if isinstance(valor, str) else pd.to_datetime(valor).strftime("%d/%m/%Y")


def carregar_item_auditado(caminho_auditoria: Path, id_statix: int) -> dict:
    dados = pd.read_excel(caminho_auditoria, sheet_name="Auditoria")
    encontrados = dados[dados["ID_STATIX"].astype("Int64") == int(id_statix)]
    if len(encontrados) != 1:
        raise ValueError(f"O ID Statix deve identificar exatamente um item auditado; encontrados: {len(encontrados)}.")
    item = encontrados.iloc[0].to_dict()
    if item.get("SITUACAO_AUDITORIA") != "PLANO_DIVERGENTE" or item.get("STATUS_STATIX") != "PAID":
        raise ValueError("Estorno bloqueado: o item nao esta pago com plano divergente na auditoria atual.")
    return item


def dados_do_item(item: dict) -> dict:
    emissao_statix = item.get("DATA_EMISSAO_STATIX")
    if pd.isna(emissao_statix) or not emissao_statix:
        emissao_statix = item["DATA_EMISSAO"]
    return {
        "LOJA": item["LOJA"],
        "FORNECEDOR": item["FORNECEDOR_ESPERADO"],
        # Para localizar o registro a estornar, usa a emissao efetivamente
        # gravada no Statix. O relancamento usa a emissao recalculada da
        # planilha homologada em executar_item_real.
        "DATA_EMISSAO": _texto_data(emissao_statix),
        "DATA_VENCIMENTO": _texto_data(item["DATA_VENCIMENTO"]),
        "DATA_PAGAMENTO": _texto_data(item["DATA_PAGAMENTO_STATIX"]),
        "VALOR": float(item["VALOR_ORIGINAL"]),
        "VALOR_JUROS": float(item["JUROS_ESPERADO"]),
        "VALOR_DESCONTO": 0.0,
        "PLANO_ATUAL": item["PLANO_STATIX"],
        "PLANO_CONTAS": item["PLANO_ESPERADO"],
        "DESCRICAO": item["DESCRICAO_ESPERADA"],
    }


def exibir_previa_estorno(caminho_auditoria: Path, id_statix: int) -> dict:
    item = carregar_item_auditado(caminho_auditoria, id_statix)
    print("PREVIA DE ESTORNO UNITARIO")
    print(f"ID Statix: {int(item['ID_STATIX'])}")
    print(f"Loja: {item['LOJA']}")
    print(f"Fornecedor: {item['FORNECEDOR_ESPERADO']}")
    print(f"Emissao: {_texto_data(item['DATA_EMISSAO'])} | Valor original: R$ {float(item['VALOR_ORIGINAL']):.2f}")
    print(f"Plano atual: {item['PLANO_STATIX']}")
    print(f"Plano correto para o relancamento: {item['PLANO_ESPERADO']}")
    print(f"Motivo registrado: {carregar_configuracao_robo().motivo_estorno}")
    return item


def estornar_item_real(caminho_auditoria: Path, id_statix: int) -> None:
    item = exibir_previa_estorno(caminho_auditoria, id_statix)
    plataforma = SeleniumStatix.do_ambiente()
    try:
        plataforma.conectar(abrir_despesas=True)
        plataforma.estornar(dados_do_item(item))
        plataforma.confirmar_estorno(dados_do_item(item))
    finally:
        plataforma.fechar()
