from enum import StrEnum
from typing import Protocol


class StatusPlataforma(StrEnum):
    NAO_ENCONTRADO = "nao_encontrado"
    PENDENTE = "pendente"
    PAGO = "pago"
    DUPLICATA = "duplicata"


class PlataformaContasAPagar(Protocol):
    def verificar(self, dados: dict) -> StatusPlataforma: ...
    def lancar(self, dados: dict) -> None: ...
    def pagar(self, dados: dict) -> None: ...
    def confirmar_pagamento(self, dados: dict, aceitar_mais_um_dia: bool = False) -> None: ...
