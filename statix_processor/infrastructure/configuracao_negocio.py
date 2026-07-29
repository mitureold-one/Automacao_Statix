"""Carregamento dos dados privados e das regras de negócio."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from statix_processor.domain.fornecedor import Fornecedor
from statix_processor.domain.lojas import Loja


CAMINHO_PADRAO = Path("config") / "negocio.json"


@dataclass(frozen=True)
class ConfiguracaoNegocio:
    lojas: dict[str, Loja]
    fornecedores: dict[str, Fornecedor]
    regras_nf: dict[str, str]
    fornecedor_nf: dict[str, str]
    fornecedor_por_loja_e_nf: dict[tuple[str, str], str]
    lojas_excluidas_exportacao: set[str]


def caminho_configuracao() -> Path:
    return Path(os.getenv("STATIX_CONFIG_NEGOCIO", str(CAMINHO_PADRAO)))


def carregar_configuracao(caminho: str | Path | None = None) -> ConfiguracaoNegocio:
    destino = Path(caminho) if caminho else caminho_configuracao()
    if not destino.is_file():
        raise FileNotFoundError(
            f"Configuração de negócio não encontrada em {destino}. "
            "Copie config/negocio.example.json para config/negocio.json "
            "e preencha os dados privados."
        )

    with destino.open(encoding="utf-8") as arquivo:
        dados = json.load(arquivo)

    lojas = {
        item["id"]: Loja(
            id_loja=item["id"],
            nome_loja=item["nome"],
            conta_banco=item["conta_banco"],
            funcionario=item.get("funcionario"),
        )
        for item in dados.get("lojas", [])
    }
    fornecedores = {
        item["id"]: Fornecedor(
            id_fornecedor=item["id"],
            nome_fornecedor=item["nome"],
            prazo_pagamento=int(item["prazo_pagamento"]),
            plano_contas=item["plano_contas"],
            descricao=item.get("descricao", ""),
        )
        for item in dados.get("fornecedores", [])
    }
    excecoes = {
        (item["loja"], item["nf"].strip().upper()): item["fornecedor"]
        for item in dados.get("fornecedor_por_loja_e_nf", [])
    }
    return ConfiguracaoNegocio(
        lojas=lojas,
        fornecedores=fornecedores,
        regras_nf={chave.upper(): valor for chave, valor in dados.get("regras_nf", {}).items()},
        fornecedor_nf=dados.get("fornecedor_nf", {}),
        fornecedor_por_loja_e_nf=excecoes,
        lojas_excluidas_exportacao=set(dados.get("lojas_excluidas_exportacao", [])),
    )
