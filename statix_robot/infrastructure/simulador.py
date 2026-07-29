from statix_robot.domain.plataforma import StatusPlataforma


class SimuladorPlataforma:
    """Adaptador sem efeitos externos, usado para revisão do lote."""

    def __init__(self):
        self.acoes = []

    def verificar(self, dados: dict) -> StatusPlataforma:
        self.acoes.append(("verificar", dados["FORNECEDOR"]))
        return StatusPlataforma.NAO_ENCONTRADO

    def lancar(self, dados: dict) -> None:
        self.acoes.append(("lancar", dados["FORNECEDOR"]))

    def pagar(self, dados: dict) -> None:
        self.acoes.append(("pagar", dados["FORNECEDOR"]))

    def confirmar_pagamento(self, dados: dict) -> None:
        self.acoes.append(("confirmar_pagamento", dados["FORNECEDOR"]))
