"""Contrato da planilha que poderá ser consumida pelo robô de automação."""

from datetime import datetime
from math import isfinite


VERSAO_CONTRATO = "1.0"
COLUNAS_HOMOLOGADAS = (
    "LOJA",
    "FORNECEDOR",
    "PLANO_CONTAS",
    "DESCRICAO",
    "BANCO",
    "DATA_VENCIMENTO",
    "DATA_EMISSAO",
    "DATA_PAGAMENTO",
    "VALOR",
    "VALOR_JUROS",
    "VALOR_DESCONTO",
)


def _vazio(valor) -> bool:
    return valor is None or not str(valor).strip()


def _data_valida(valor: str) -> bool:
    try:
        datetime.strptime(str(valor), "%d/%m/%Y")
        return True
    except ValueError:
        return False


def validar_lancamentos_operacionais(resultados) -> list[str]:
    """Valida pares ``(linha_origem, Lancamento_Saida)`` para exportação."""
    erros = []
    obrigatorios = ("LOJA", "FORNECEDOR", "PLANO_CONTAS", "BANCO", "DATA_VENCIMENTO", "DATA_EMISSAO")
    campos_numericos = ("VALOR", "VALOR_JUROS", "VALOR_DESCONTO")

    for linha_origem, lancamento in resultados:
        for campo in obrigatorios:
            if _vazio(getattr(lancamento, campo)):
                erros.append(f"Linha {linha_origem}: campo obrigatório {campo} vazio.")

        for campo in ("DATA_VENCIMENTO", "DATA_EMISSAO"):
            if not _vazio(getattr(lancamento, campo)) and not _data_valida(getattr(lancamento, campo)):
                erros.append(f"Linha {linha_origem}: {campo} deve usar o formato DD/MM/AAAA.")

        pagamento = lancamento.DATA_PAGAMENTO
        if not _vazio(pagamento) and not _data_valida(pagamento):
            erros.append(f"Linha {linha_origem}: DATA_PAGAMENTO deve usar o formato DD/MM/AAAA.")

        for campo in campos_numericos:
            try:
                numero = float(getattr(lancamento, campo))
                if not isfinite(numero) or numero < 0:
                    raise ValueError
            except (TypeError, ValueError):
                erros.append(f"Linha {linha_origem}: {campo} deve ser numérico e maior ou igual a zero.")

        if _data_valida(lancamento.DATA_EMISSAO) and _data_valida(lancamento.DATA_VENCIMENTO):
            emissao = datetime.strptime(lancamento.DATA_EMISSAO, "%d/%m/%Y")
            vencimento = datetime.strptime(lancamento.DATA_VENCIMENTO, "%d/%m/%Y")
            if emissao > vencimento:
                erros.append(f"Linha {linha_origem}: DATA_EMISSAO não pode ser posterior ao vencimento.")

    return erros
