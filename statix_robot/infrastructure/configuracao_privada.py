"""Configuração privada do robô, carregada do arquivo ignorado pelo Git."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from statix_processor.infrastructure.configuracao_negocio import caminho_configuracao


@dataclass(frozen=True)
class ConfiguracaoAuditoria:
    inicio: str
    fim: str
    filtro_plano: str
    filtro_fornecedor: str
    arquivo: Path = Path("auditoria.xlsx")


@dataclass(frozen=True)
class ConfiguracaoRobo:
    normalizacoes: dict[str, str] = field(default_factory=dict)
    consulta_historico: dict = field(default_factory=dict)
    auditoria: ConfiguracaoAuditoria | None = None
    motivo_estorno: str = "Correção de classificação contábil."


def carregar_configuracao_robo(caminho: str | Path | None = None) -> ConfiguracaoRobo:
    destino = Path(caminho) if caminho else caminho_configuracao()
    try:
        with destino.open(encoding="utf-8") as arquivo:
            dados = json.load(arquivo).get("robo", {})
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Não foi possível carregar a configuração privada do robô: {exc}") from exc

    auditoria_dados = dados.get("auditoria")
    auditoria = None
    if auditoria_dados:
        auditoria = ConfiguracaoAuditoria(
            inicio=auditoria_dados["inicio"],
            fim=auditoria_dados["fim"],
            filtro_plano=auditoria_dados["filtro_plano"],
            filtro_fornecedor=auditoria_dados["filtro_fornecedor"],
            arquivo=Path(auditoria_dados.get("arquivo", "auditoria.xlsx")),
        )
        date.fromisoformat(auditoria.inicio)
        date.fromisoformat(auditoria.fim)

    return ConfiguracaoRobo(
        normalizacoes={
            str(origem).upper(): str(valor).upper()
            for origem, valor in dados.get("normalizacoes", {}).items()
        },
        consulta_historico=dados.get("consulta_historico", {}),
        auditoria=auditoria,
        motivo_estorno=dados.get("motivo_estorno", "Correção de classificação contábil."),
    )
