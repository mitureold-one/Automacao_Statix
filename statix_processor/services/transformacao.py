import re
from datetime import timedelta

# Serviço responsável por aplicar regras de negócio.

from statix_processor.domain.lancamento_entrada import Lancamento_Entrada
from statix_processor.domain.lancamento_saida import Lancamento_Saida
from statix_processor.infrastructure.configuracao_negocio import (
    ConfiguracaoNegocio,
    carregar_configuracao,
)

class Transformador:
    def __init__(self, configuracao: ConfiguracaoNegocio | None = None):
        self.configuracao = configuracao or carregar_configuracao()

    def transformar(self, entrada: Lancamento_Entrada) -> Lancamento_Saida:

        return Lancamento_Saida(
            LOJA=self._obter_loja(entrada),
            FORNECEDOR=self._obter_fornecedor(entrada),
            PLANO_CONTAS=self._obter_plano_contas(entrada),
            DESCRICAO=self._gerar_descricao(entrada),
            BANCO=self._obter_banco(entrada),
            DATA_VENCIMENTO=self._formatar_data(entrada.DATA_VENCIMENTO),
            DATA_EMISSAO=self._obter_data_emissao(entrada),
            DATA_PAGAMENTO=self._formatar_data(entrada.DATA_PAGAMENTO),
            VALOR=self._calcular_valor(entrada),
            VALOR_JUROS=self._calcular_juros(entrada),
            VALOR_DESCONTO=self._calcular_desconto(entrada)
        )
    def _obter_fornecedor_obj(self, entrada: Lancamento_Entrada):
        origem = self._normalizar_texto(entrada.ORIGEM)
        return self.configuracao.fornecedores.get(origem)

    def _obter_loja_obj(self, entrada: Lancamento_Entrada):
        return self.configuracao.lojas.get(entrada.LOJA)

    def _obter_loja(self, entrada: Lancamento_Entrada) -> str:
        loja = self._obter_loja_obj(entrada)
        return loja.nome_loja if loja else "Loja Desconhecida! Cadastre !"

    def _obter_fornecedor(self, entrada: Lancamento_Entrada) -> str:
        # A NF pode sobrescrever quem e o fornecedor de verdade (ex: um
        # lancamento de "Folha de Pessoal" com "INSS" na NF nao vai pro
        # funcionario, vai pro governo).
        nf = self._normalizar_texto(entrada.NF)
        fornecedor_especial = self.configuracao.fornecedor_por_loja_e_nf.get((entrada.LOJA, nf))
        if fornecedor_especial:
            return fornecedor_especial

        regra_nf = self._obter_regra_nf(nf)
        if regra_nf in self.configuracao.fornecedor_nf:
            return self.configuracao.fornecedor_nf[regra_nf]

        fornecedor = self._obter_fornecedor_obj(entrada)
        if not fornecedor:
            return "Fornecedor Desconhecido! Cadastre !"

        # Folha de pessoal pode usar o colaborador privado vinculado à loja.
        if fornecedor.id_fornecedor == "FOLHA DE PESSOAL":
            loja = self._obter_loja_obj(entrada)
            if loja and loja.funcionario:
                return loja.funcionario

        return fornecedor.nome_fornecedor

    def _obter_plano_contas(self, entrada: Lancamento_Entrada) -> str:
        nf = self._normalizar_texto(entrada.NF)
        regra_nf = self._obter_regra_nf(nf)
        if regra_nf:
            return regra_nf

        fornecedor = self._obter_fornecedor_obj(entrada)
        if fornecedor:
            return fornecedor.plano_contas

        return "Plano de Contas Desconhecido! Cadastre !"
    
    def _gerar_descricao(self, entrada: Lancamento_Entrada) -> str:
        # A pessoa que preenche a planilha as vezes anota a explicacao real
        # do gasto na coluna NF (parcelamento, item comprado, evento etc.)
        # em vez de deixar a NF em branco/numero de documento. Quando isso
        # acontece, essa anotacao e mais informativa que o fornecedor
        # generico da ORIGEM (ex: "Manutencao"), entao ela tem prioridade.
        nf = self._normalizar_texto(entrada.NF)
        if nf and not self._eh_numerico(entrada.NF):
            # Usa o texto real da NF, nao o nome resumido da categoria do
            # plano de contas -- "PREVENTIVA ARCOND" diz mais que
            # "MANUTENCAO EM GERAL". O plano de contas ja fica registrado
            # em PLANO_CONTAS de qualquer forma.
            return nf

        fornecedor = self._obter_fornecedor_obj(entrada)
        return fornecedor.descricao if fornecedor else ""

    _PADRAO_TRANSFERENCIA = re.compile(r"^\d+\s+TRANSFERIDA$")
    _PADRAO_SO_DIGITOS = re.compile(r"^[\d\s]+$")

    def _eh_numerico(self, valor) -> bool:
        """
        Verifica se a NF NAO deve virar descricao: numero de documento,
        data digitada por engano na coluna (ex: "20260401 000000"), ou
        uma referencia de transferencia bancaria (ex: "379053 TRANSFERIDA").
        """
        if valor is None:
            return True
        texto = str(valor).strip()
        if not texto or texto.upper() == "NAN":
            return True

        texto_upper = texto.upper()
        if self._PADRAO_TRANSFERENCIA.match(texto_upper):
            return True
        if self._PADRAO_SO_DIGITOS.match(texto_upper):
            return True

        limpo = texto.replace(".", "").replace(",", ".")
        try:
            float(limpo)
            return True
        except ValueError:
            return False
    
    def _obter_banco(self, entrada: Lancamento_Entrada) -> str:
        # O banco eh vinculado a LOJA (conta de pagamento fixa por loja),
        # nao ao texto generico da coluna Banco da planilha de origem.
        loja = self._obter_loja_obj(entrada)
        return loja.conta_banco if loja else "Banco Desconhecido! Cadastre !"

    def _formatar_data(self, data: str) -> str:
        # Implementar lÃ³gica para formatar a data conforme necessÃ¡rio
        return data.strftime("%d/%m/%Y") if data else ""
    
    def _obter_data_emissao(self, entrada: Lancamento_Entrada) -> str:
        if not entrada.DATA_VENCIMENTO:
            return ""

        # A planilha de entrada possui somente pagamento (DATA) e vencimento
        # (VENC). A emissao e sempre calculada pelo prazo do fornecedor da
        # ORIGEM, centralizado no catalogo; a NF pode alterar plano/fornecedor
        # exibidos, mas nao altera esse prazo.
        fornecedor = self._obter_fornecedor_obj(entrada)
        dias = fornecedor.prazo_pagamento if fornecedor else 0

        data_emissao = entrada.DATA_VENCIMENTO - timedelta(days=dias)
        return data_emissao.strftime("%d/%m/%Y")
    
    def _calcular_valor(self, entrada: Lancamento_Entrada) -> float:
        return entrada.VALOR
    
    def _calcular_juros(self, entrada: Lancamento_Entrada) -> float:
        # JUROS positivo = juros de fato; negativo Ã© desconto (ver _calcular_desconto)
        return max(entrada.JUROS, 0.0)
    
    def _calcular_desconto(self, entrada: Lancamento_Entrada) -> float:
        # Espelha a regra do Satix antigo: valor de JUROS negativo vira desconto
        return abs(min(entrada.JUROS, 0.0))

    def _normalizar_texto(self, texto: str) -> str:
        return str(texto or "").strip().upper()

    def _obter_regra_nf(self, nf: str) -> str:
        for chave, plano_contas in self.configuracao.regras_nf.items():
            if chave in nf:
                return plano_contas
        return ""
    
