"""Auditoria configurável e somente leitura de lançamentos."""

import json
import re
import unicodedata
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from statix_robot.infrastructure.planilha_homologada import carregar_planilha_homologada
from statix_robot.infrastructure.configuracao_privada import carregar_configuracao_robo
from statix_robot.infrastructure.selenium_statix import SeleniumStatix


def _normalizar(valor, substituicoes=None) -> str:
    texto = unicodedata.normalize("NFD", str(valor or "").upper())
    texto = "".join(caractere for caractere in texto if unicodedata.category(caractere) != "Mn")
    for origem, destino in (substituicoes or {}).items():
        texto = texto.replace(origem, destino)
    return re.sub(r"[^A-Z0-9]", "", texto)


def _data_br(valor) -> str:
    data = pd.to_datetime(valor, errors="coerce")
    return "" if pd.isna(data) else data.strftime("%d/%m/%Y")


def _numero(valor) -> float | None:
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def _esperados(caminho_saida: Path, configuracao, normalizacoes) -> list:
    lancamentos = carregar_planilha_homologada(caminho_saida)
    inicio, fim = pd.Timestamp(configuracao.inicio), pd.Timestamp(configuracao.fim)
    return [
        item for item in lancamentos
        if _normalizar(item.PLANO_CONTAS, normalizacoes)
        == _normalizar(configuracao.filtro_plano, normalizacoes)
        and _normalizar(configuracao.filtro_fornecedor, normalizacoes)
        in _normalizar(item.FORNECEDOR, normalizacoes)
        and inicio <= pd.to_datetime(item.DATA_VENCIMENTO, dayfirst=True) <= fim
    ]


def _encontrar_no_statix(item, registros: list[dict], normalizacoes=None) -> list[dict]:
    emissao = item.DATA_EMISSAO
    loja = _normalizar(item.LOJA, normalizacoes)
    fornecedor = _normalizar(item.FORNECEDOR, normalizacoes)
    candidatos = []
    candidatos_sem_emissao = []
    for registro in registros:
        if _normalizar(registro.get("branchName"), normalizacoes) != loja:
            continue
        fornecedor_statix = _normalizar(registro.get("recipientDescription"), normalizacoes)
        if fornecedor not in fornecedor_statix and fornecedor_statix not in fornecedor:
            continue
        candidatos_sem_emissao.append(registro)
        if _data_br(registro.get("issueDate")) == emissao:
            candidatos.append(registro)
    total_esperado = round(item.VALOR + item.VALOR_JUROS - item.VALOR_DESCONTO, 2)
    por_valor = []
    for candidato in candidatos:
        valores = [_numero(candidato.get(campo)) for campo in ("receivableTotalAmount", "receivableNetAmount")]
        if any(valor is not None and abs(valor - total_esperado) < 0.01 for valor in valores):
            por_valor.append(candidato)
    # Data, loja e fornecedor sem o mesmo total nao identificam um
    # lancamento com seguranca. Nunca reutilize esse candidato no lote.
    if por_valor:
        return por_valor

    # Alguns lançamentos históricos podem ter emissão divergente. Sem
    # candidato pela data, mantemos a conciliação
    # apenas quando loja, fornecedor e valor total coincidirem exatamente.
    por_valor_sem_emissao = []
    for candidato in candidatos_sem_emissao:
        valores = [_numero(candidato.get(campo)) for campo in ("receivableTotalAmount", "receivableNetAmount")]
        if any(valor is not None and abs(valor - total_esperado) < 0.01 for valor in valores):
            por_valor_sem_emissao.append(candidato)
    return por_valor_sem_emissao


def auditar(caminho_saida: Path) -> Path:
    configuracao_robo = carregar_configuracao_robo()
    configuracao = configuracao_robo.auditoria
    if configuracao is None:
        raise ValueError("Defina robo.auditoria na configuração privada.")
    esperados = _esperados(caminho_saida, configuracao, configuracao_robo.normalizacoes)
    if not esperados:
        raise ValueError("Nenhum lançamento encontrado para os filtros privados da auditoria.")

    plataforma = SeleniumStatix.do_ambiente()
    try:
        plataforma.conectar(abrir_despesas=True)
        plataforma.verificar(asdict(esperados[0]))
        corpo, cabecalhos = plataforma.detalhes_da_ultima_requisicao("/payables/list")
        consulta = json.loads(corpo)
        primeira_emissao = min(
            pd.to_datetime(item.DATA_EMISSAO, dayfirst=True) for item in esperados
        ).strftime("%Y-%m-%d")
        consulta.update({
            # A selecao da auditoria e pelo vencimento. A busca no Statix precisa
            # abranger também emissões anteriores ao período de vencimento,
            # para que esses registros não sejam omitidos.
            "issuedPeriod": {"from": f"{primeira_emissao}T03:00:00.000Z", "to": "2026-07-02T02:59:59.999Z"},
            "paymentStatus": ["PENDING", "PAID"],
            "branches": [],
            "accountPlans": [],
            "recipients": [],
            "size": 1000,
            "page": 1,
        })
        resposta = plataforma.repetir_consulta_api("/conciliador-ws/payables/list", json.dumps(consulta), cabecalhos)
        if resposta.get("status") != 200:
            raise RuntimeError(f"Consulta de auditoria recusada pela API: HTTP {resposta.get('status')}")
        registros = json.loads(resposta["corpo"]).get("content", [])
    finally:
        plataforma.fechar()

    linhas = []
    for item in esperados:
        candidatos = _encontrar_no_statix(item, registros, configuracao_robo.normalizacoes)
        base = {
            "LOJA": item.LOJA,
            "FORNECEDOR_ESPERADO": item.FORNECEDOR,
            "PLANO_ESPERADO": item.PLANO_CONTAS,
            "DESCRICAO_ESPERADA": item.DESCRICAO,
            "DATA_EMISSAO": item.DATA_EMISSAO,
            "DATA_VENCIMENTO": item.DATA_VENCIMENTO,
            "VALOR_ORIGINAL": item.VALOR,
            "JUROS_ESPERADO": item.VALOR_JUROS,
        }
        if len(candidatos) != 1:
            valores_candidatos = ", ".join(str(candidato.get("receivableTotalAmount", "")) for candidato in candidatos[:5])
            linhas.append({**base, "SITUACAO_AUDITORIA": "NAO_ENCONTRADO" if not candidatos else "AMBIGUO", "CANDIDATOS_STATIX": len(candidatos), "VALORES_TOTAIS_CANDIDATOS": valores_candidatos})
            continue
        registro = candidatos[0]
        numero_plano = str(registro.get("formattedAccountNumber", "")).strip()
        nome_plano = str(registro.get("accountPlanName", "")).strip()
        plano_statix = f"{numero_plano} - {nome_plano}" if numero_plano else nome_plano
        plano_correto = _normalizar(
            plano_statix, configuracao_robo.normalizacoes
        ) == _normalizar(item.PLANO_CONTAS, configuracao_robo.normalizacoes)
        linhas.append({
            **base,
            "SITUACAO_AUDITORIA": "CORRETO" if plano_correto else "PLANO_DIVERGENTE",
            "CANDIDATOS_STATIX": 1,
            "PLANO_STATIX": plano_statix,
            "STATUS_STATIX": registro.get("paymentStatus", ""),
            "DESCRICAO_STATIX": registro.get("transactionDescription", ""),
            "DATA_EMISSAO_STATIX": _data_br(registro.get("issueDate")),
            "DATA_PAGAMENTO_STATIX": _data_br(registro.get("paymentDate")),
            "VALOR_TOTAL_STATIX": registro.get("receivableTotalAmount"),
            "ID_STATIX": registro.get("receivablePayableId"),
        })

    resultado = pd.DataFrame(linhas)
    resumo = resultado.groupby("SITUACAO_AUDITORIA").size().reset_index(name="QUANTIDADE")
    with pd.ExcelWriter(configuracao.arquivo) as escritor:
        resultado.to_excel(escritor, sheet_name="Auditoria", index=False)
        resumo.to_excel(escritor, sheet_name="Resumo", index=False)
    print(f"[OK] Auditoria concluída: {len(resultado)} lançamento(s) analisado(s).")
    print(resumo.to_string(index=False))
    print(f"[OK] Relatório gerado: {configuracao.arquivo.resolve()}")
    return configuracao.arquivo
