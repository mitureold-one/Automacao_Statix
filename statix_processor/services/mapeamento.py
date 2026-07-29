"""Mapeamento entre os modelos de entrada e saída."""

from statix_processor.domain.lancamento_entrada import Lancamento_Entrada
from statix_processor.domain.lancamento_saida import Lancamento_Saida


class Lancamento_Mapper:
    def __init__(self, transformador):
        self.transformador = transformador

    def mapear(self, entrada: Lancamento_Entrada) -> Lancamento_Saida:
        return self.transformador.transformar(entrada)

    def mapear_lista(self, entradas: list[Lancamento_Entrada]) -> list[Lancamento_Saida]:
        return [self.mapear(entrada) for entrada in entradas]
