from dataclasses import dataclass


@dataclass(frozen=True)
class ConfiguracaoExecucao:
    somente_pagamento: bool = False
    iniciar_da_linha: int = 0
    simulacao: bool = True
    aceitar_pagamento_mais_um_dia: bool = False
