"""Caso de uso completo: transformar, revisar, homologar e registrar."""

from dataclasses import asdict
from pathlib import Path

import pandas as pd

from statix_processor.domain.lancamento_entrada import Lancamento_Entrada
from statix_processor.config import (
    ARQUIVO_ENTRADA,
    ARQUIVO_PREVIEW,
    ARQUIVO_SAIDA,
    COLUNAS_OBRIGATORIAS,
    LIMITE_EXEMPLOS,
    MARCADOR_PENDENCIA,
)
from statix_processor.domain.contrato import validar_lancamentos_operacionais
from statix_processor.infrastructure.excel import Exportador_Excel, Importador_Excel
from statix_processor.infrastructure.historico import registrar_execucao
from statix_processor.services.normalizacao import Normalizador_Lancamentos
from statix_processor.services.mapeamento import Lancamento_Mapper
from statix_processor.services.transformacao import Transformador
from statix_processor.infrastructure.configuracao_negocio import carregar_configuracao


CONFIGURACAO_NEGOCIO = None


def _vazio(valor):
    return valor is None or (isinstance(valor, str) and not valor.strip()) or pd.isna(valor)


def _data(valor):
    if _vazio(valor):
        return None
    data = pd.to_datetime(valor, errors="coerce", dayfirst=True)
    return None if pd.isna(data) else data.to_pydatetime()


def _numero(valor, campo):
    if _vazio(valor):
        raise ValueError(f"campo {campo} vazio")
    try:
        return float(valor)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"campo {campo} inválido: {valor!r}") from exc


def _entrada(linha):
    vencimento = _data(linha.get("VENC"))
    if vencimento is None:
        raise ValueError("campo VENC vazio ou com data inválida")
    juros = linha.get("JURO", 0)
    return Lancamento_Entrada(
        LOJA=str(linha.get("LOJA", "")), NF=str(linha.get("NF", "")),
        VALOR=_numero(linha.get("VLR"), "VLR"), ORIGEM=str(linha.get("ORIGEM", "")),
        DATA_VENCIMENTO=vencimento, MES_REFERENCIA=str(linha.get("MES", "")),
        DATA_PAGAMENTO=_data(linha.get("DATA")), BANCO=str(linha.get("BANCO", "")),
        JUROS=0.0 if _vazio(juros) else _numero(juros, "JURO"),
    )


def _pendencias(lancamento):
    campos = {"LOJA": lancamento.LOJA, "FORNECEDOR": lancamento.FORNECEDOR,
              "PLANO_CONTAS": lancamento.PLANO_CONTAS, "BANCO": lancamento.BANCO}
    return [nome for nome, valor in campos.items() if MARCADOR_PENDENCIA in str(valor).upper()]


def _status(lancamento):
    pendencias = _pendencias(lancamento)
    if CONFIGURACAO_NEGOCIO and lancamento.LOJA in CONFIGURACAO_NEGOCIO.lojas_excluidas_exportacao:
        alerta = "Loja configurada fora da exportação operacional"
        if pendencias:
            alerta += f"; cadastro pendente: {', '.join(pendencias)}"
        return "FORA_DA_EXPORTACAO", alerta
    if pendencias:
        return "PENDENTE_CADASTRO", f"Cadastro pendente: {', '.join(pendencias)}"
    return "APROVADO", ""


def _avisos(df):
    avisos = []
    for coluna in ("LOJA", "ORIGEM", "NF"):
        if coluna in df.columns:
            total = sum(_vazio(valor) for valor in df[coluna])
            if total:
                avisos.append(f"{total} linha(s) com {coluna} vazio.")
    chaves = [coluna for coluna in ("LOJA", "NF", "VLR", "VENC") if coluna in df.columns]
    if chaves:
        duplicadas = int(df.duplicated(subset=chaves, keep=False).sum())
        if duplicadas:
            avisos.append(f"{duplicadas} linha(s) possivelmente duplicada(s), considerando {', '.join(chaves)}.")
    return avisos


def _preview(resultados, erros, avisos, bloqueios):
    registros = []
    for linha, lancamento in resultados:
        status, alerta = _status(lancamento)
        registro = asdict(lancamento)
        registro.update(LINHA_ORIGEM=linha, STATUS_REVISAO=status, ALERTAS=alerta)
        registros.append(registro)
    registros.extend({"LINHA_ORIGEM": erro["linha"], "STATUS_REVISAO": "ERRO_DE_PROCESSAMENTO", "ALERTAS": erro["mensagem"]} for erro in erros)
    resumo = [
        {"CATEGORIA": "Linhas transformadas", "QUANTIDADE": len(resultados), "DETALHE": ""},
        {"CATEGORIA": "Erros de processamento", "QUANTIDADE": len(erros), "DETALHE": ""},
        {"CATEGORIA": "Avisos para revisão", "QUANTIDADE": len(avisos), "DETALHE": " | ".join(avisos)},
        {"CATEGORIA": "Bloqueios da homologação", "QUANTIDADE": len(bloqueios), "DETALHE": " | ".join(bloqueios)},
    ]
    destino = Path(ARQUIVO_PREVIEW)
    with pd.ExcelWriter(destino) as escritor:
        pd.DataFrame(registros).to_excel(escritor, sheet_name="Lançamentos", index=False)
        pd.DataFrame(resumo).to_excel(escritor, sheet_name="Resumo", index=False)
    return destino


def _historico(entrada, resultados, erros, avisos, bloqueios, arquivo_saida):
    lancamentos = [lancamento for _, lancamento in resultados]
    try:
        return registrar_execucao(
            entrada=entrada, status="BLOQUEADO" if bloqueios else "HOMOLOGADO",
            transformados=len(lancamentos), aprovados=sum(_status(item)[0] == "APROVADO" for item in lancamentos),
            fora_exportacao=sum(_status(item)[0] == "FORA_DA_EXPORTACAO" for item in lancamentos),
            erros=len(erros), avisos=avisos, bloqueios=bloqueios, arquivo_saida=arquivo_saida,
        )
    except Exception as exc:
        print(f"[AVISO] Não foi possível registrar o histórico: {type(exc).__name__}: {exc}")
        return None


def _imprimir_itens(titulo, itens):
    if not itens:
        return
    print(titulo)
    for item in itens[:LIMITE_EXEMPLOS]:
        print(f"  - {item}")
    if len(itens) > LIMITE_EXEMPLOS:
        print(f"  ... e mais {len(itens) - LIMITE_EXEMPLOS} ocorrência(s).")


def executar() -> int:
    global CONFIGURACAO_NEGOCIO
    print("\n" + "=" * 72 + "\nSTATIX | TRANSFORMAÇÃO E HOMOLOGAÇÃO DE PLANILHA\n" + "=" * 72)
    try:
        CONFIGURACAO_NEGOCIO = carregar_configuracao()
    except (OSError, ValueError) as exc:
        print(f"[ERRO] Configuração de negócio: {exc}")
        return 1
    arquivo_entrada = Path(ARQUIVO_ENTRADA)
    if not arquivo_entrada.exists():
        print(f"[ERRO] Arquivo de entrada não encontrado: {arquivo_entrada.resolve()}")
        return 1
    try:
        bruto = Importador_Excel().importar(arquivo_entrada)
        dados = Normalizador_Lancamentos().normalizar(bruto)
    except Exception as exc:
        print(f"[ERRO] Leitura ou normalização: {type(exc).__name__}: {exc}")
        return 1
    faltantes = sorted(COLUNAS_OBRIGATORIAS - set(dados.columns))
    if faltantes:
        print(f"[ERRO] Colunas obrigatórias ausentes: {', '.join(faltantes)}")
        return 1

    avisos, resultados, erros = _avisos(dados), [], []
    mapper = Lancamento_Mapper(Transformador(CONFIGURACAO_NEGOCIO))
    for indice, linha in dados.iterrows():
        try:
            resultados.append((indice + 2, mapper.mapear(_entrada(linha))))
        except Exception as exc:
            erros.append({"linha": indice + 2, "mensagem": f"Linha {indice + 2}: {type(exc).__name__}: {exc}"})

    operacionais, bloqueios = [], []
    for resultado in resultados:
        status, alerta = _status(resultado[1])
        if status == "APROVADO":
            operacionais.append(resultado)
        elif status == "PENDENTE_CADASTRO":
            bloqueios.append(f"{resultado[1].LOJA}: {alerta}")
    if erros:
        bloqueios.append(f"{len(erros)} linha(s) com erro de processamento.")
    bloqueios.extend(validar_lancamentos_operacionais(operacionais))
    if not operacionais:
        bloqueios.append("Nenhum lançamento aprovado para exportação operacional.")

    preview = _preview(resultados, erros, avisos, bloqueios)
    aprovados = len(operacionais)
    fora = sum(_status(lancamento)[0] == "FORA_DA_EXPORTACAO" for _, lancamento in resultados)
    print(f"[OK] {len(resultados)} transformados | {aprovados} aprovados | {fora} fora da exportação | {len(erros)} erro(s)")
    print(f"[OK] Preview gerado: {preview.resolve()}")
    pendentes = [
        f"Linha {linha}: {lancamento.LOJA} — {', '.join(_pendencias(lancamento))}"
        for linha, lancamento in resultados if _pendencias(lancamento)
    ]
    _imprimir_itens("[AVISO] PENDÊNCIAS DE CADASTRO", pendentes)
    _imprimir_itens("[AVISO] DADOS A CONFERIR", avisos)
    _imprimir_itens("[ERRO] LINHAS IGNORADAS", [erro["mensagem"] for erro in erros])
    _imprimir_itens("[BLOQUEIO] CORRIJA ANTES DA AUTOMAÇÃO", bloqueios)
    if bloqueios:
        _historico(arquivo_entrada, resultados, erros, avisos, bloqueios, None)
        print("[BLOQUEADO] Revise o preview antes de atualizar a saída operacional.")
        return 2
    saida = Exportador_Excel(ARQUIVO_SAIDA).exportar_dados([lancamento for _, lancamento in operacionais])
    historico = _historico(arquivo_entrada, resultados, erros, avisos, [], str(Path(saida).resolve()))
    print(f"[OK] Saída homologada: {Path(saida).resolve()}")
    if historico:
        print(f"[OK] Histórico atualizado: {historico.resolve()}")
    return 0
