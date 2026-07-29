"""Modelo de lançamento homologado."""

from dataclasses import dataclass
@dataclass
class Lancamento_Saida:
    LOJA:            str
    FORNECEDOR:      str
    PLANO_CONTAS:    str
    DESCRICAO:       str
    BANCO:           str
    DATA_VENCIMENTO: str
    DATA_EMISSAO:    str
    DATA_PAGAMENTO:  str
    VALOR:           float = 0.0
    VALOR_JUROS:     float = 0.0
    VALOR_DESCONTO:  float = 0.0
