"""Registro imutável, em JSONL, das execuções do pipeline."""

import hashlib
import json
from datetime import datetime
from pathlib import Path


ARQUIVO_HISTORICO = Path("historico_execucoes.jsonl")


def _sha256(arquivo: Path) -> str:
    digest = hashlib.sha256()
    with arquivo.open("rb") as origem:
        for bloco in iter(lambda: origem.read(64 * 1024), b""):
            digest.update(bloco)
    return digest.hexdigest()


def registrar_execucao(
    *,
    entrada: Path,
    status: str,
    transformados: int,
    aprovados: int,
    fora_exportacao: int,
    erros: int,
    avisos: list[str],
    bloqueios: list[str],
    arquivo_saida: str | None,
) -> Path:
    registro = {
        "executado_em": datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": status,
        "arquivo_entrada": str(entrada.resolve()),
        "sha256_entrada": _sha256(entrada),
        "arquivo_saida": arquivo_saida,
        "transformados": transformados,
        "aprovados": aprovados,
        "fora_exportacao": fora_exportacao,
        "erros": erros,
        "avisos": avisos,
        "bloqueios": bloqueios,
    }
    with ARQUIVO_HISTORICO.open("a", encoding="utf-8") as destino:
        destino.write(json.dumps(registro, ensure_ascii=False) + "\n")
    return ARQUIVO_HISTORICO
