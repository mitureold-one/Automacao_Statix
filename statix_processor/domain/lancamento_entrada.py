"""Modelo de lançamento na origem."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Lancamento_Entrada:
    LOJA : str
    NF : str
    VALOR: float
    ORIGEM: str
    DATA_VENCIMENTO: datetime
    MES_REFERENCIA: str
    DATA_PAGAMENTO: datetime
    BANCO: str
    JUROS: float

