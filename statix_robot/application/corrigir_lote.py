"""Correcao sequencial e interrompivel de um pequeno lote auditado."""

import json
from pathlib import Path

import pandas as pd

from statix_robot.application.estornar_item import carregar_item_auditado, estornar_item_real
from statix_robot.application.executar_item import executar_item_real, selecionar_item


def _carregar_progresso(caminho: Path) -> dict:
    if not caminho.exists():
        return {"estornados": [], "concluidos": []}
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
        return {
            "estornados": [int(item) for item in dados.get("estornados", [])],
            "concluidos": [int(item) for item in dados.get("concluidos", [])],
        }
    except (json.JSONDecodeError, OSError, ValueError):
        raise RuntimeError(f"Progresso do lote invalido: {caminho.resolve()}")


def _salvar_progresso(caminho: Path, progresso: dict) -> None:
    caminho.write_text(json.dumps(progresso, ensure_ascii=False, indent=2), encoding="utf-8")


def executar_lote_correcao(
    caminho_auditoria: Path, caminho_saida: Path, ids_statix: list[int], aceitar_pagamento_mais_um_dia: bool,
    caminho_progresso: Path = Path("progresso_correcoes_lote.json"),
) -> dict:
    if not ids_statix:
        raise ValueError("Informe ao menos um ID Statix para o lote de correcao.")
    if len(set(ids_statix)) != len(ids_statix):
        raise ValueError("O lote de correcao nao pode conter IDs repetidos.")

    progresso = _carregar_progresso(caminho_progresso)
    concluidos = list(progresso["concluidos"])
    for posicao, id_statix in enumerate(ids_statix, start=1):
        if id_statix in progresso["concluidos"]:
            print(f"[LOTE {posicao}/{len(ids_statix)}] ID Statix {id_statix} ja concluido; pulando.")
            continue
        item_antigo = carregar_item_auditado(caminho_auditoria, id_statix)
        criterios_base = {
            "LOJA": item_antigo["LOJA"],
            "FORNECEDOR": item_antigo["FORNECEDOR_ESPERADO"],
            "DATA_VENCIMENTO": pd.to_datetime(
                item_antigo["DATA_VENCIMENTO"], dayfirst=True
            ).strftime("%d/%m/%Y"),
            "VALOR": float(item_antigo["VALOR_ORIGINAL"]),
        }
        novo = selecionar_item(caminho_saida, criterios_base)
        criterios_novos = {
            "LOJA": novo.LOJA,
            "FORNECEDOR": novo.FORNECEDOR,
            "DATA_EMISSAO": novo.DATA_EMISSAO,
            "VALOR": novo.VALOR,
        }
        print(f"[LOTE {posicao}/{len(ids_statix)}] ID Statix {id_statix}")
        if id_statix not in progresso["estornados"]:
            estornar_item_real(caminho_auditoria, id_statix)
            progresso["estornados"].append(id_statix)
            _salvar_progresso(caminho_progresso, progresso)
        executar_item_real(
            caminho_saida,
            Path("progresso_robo_item.json"),
            criterios_novos,
            aceitar_pagamento_mais_um_dia,
        )
        concluidos.append(id_statix)
        progresso["concluidos"].append(id_statix)
        _salvar_progresso(caminho_progresso, progresso)
    return {"concluidos": concluidos}
