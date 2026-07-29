from dataclasses import asdict

from statix_robot.domain.configuracao import ConfiguracaoExecucao
from statix_robot.domain.plataforma import StatusPlataforma


class ExecutorRobo:
    def __init__(self, plataforma, repositorio_progresso, configuracao: ConfiguracaoExecucao):
        self.plataforma = plataforma
        self.repositorio_progresso = repositorio_progresso
        self.configuracao = configuracao

    def executar(self, lancamentos) -> dict:
        progresso = self.repositorio_progresso.carregar()
        concluidos = {item["idx"] for item in progresso["concluidos"]}
        resumo = {"total": len(lancamentos), "simulados": 0, "concluidos": 0, "pulados": 0, "erros": 0}

        for indice, lancamento in enumerate(lancamentos):
            rotulo = f"[{indice + 1}/{len(lancamentos)}] {lancamento.FORNECEDOR[:35]}"
            if indice in concluidos:
                resumo["pulados"] += 1
                continue
            dados = asdict(lancamento)
            status = self.plataforma.verificar(dados)
            if status == StatusPlataforma.DUPLICATA:
                motivo = "Duplicata detectada; intervenção manual necessária."
                if not self.configuracao.simulacao:
                    self.repositorio_progresso.registrar_erro(progresso, indice, rotulo, motivo)
                raise RuntimeError(f"{rotulo}: {motivo}")
            if status == StatusPlataforma.PAGO:
                resumo["pulados"] += 1
                if not self.configuracao.simulacao:
                    self.repositorio_progresso.registrar_sucesso(progresso, indice, rotulo)
                continue

            deve_lancar = (
                status == StatusPlataforma.NAO_ENCONTRADO
                and not self.configuracao.somente_pagamento
                and indice >= self.configuracao.iniciar_da_linha
            )
            if deve_lancar:
                self.plataforma.lancar(dados)
            self.plataforma.pagar(dados)
            if not self.configuracao.simulacao:
                self.plataforma.confirmar_pagamento(
                    dados,
                    aceitar_mais_um_dia=self.configuracao.aceitar_pagamento_mais_um_dia,
                )

            if self.configuracao.simulacao:
                resumo["simulados"] += 1
            else:
                self.repositorio_progresso.registrar_sucesso(progresso, indice, rotulo)
                resumo["concluidos"] += 1
        return resumo
