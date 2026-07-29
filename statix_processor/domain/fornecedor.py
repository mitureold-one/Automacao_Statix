class Fornecedor:
    def __init__(self, id_fornecedor, nome_fornecedor, prazo_pagamento, plano_contas, descricao):
        self.id_fornecedor = id_fornecedor
        self.nome_fornecedor = nome_fornecedor
        self.prazo_pagamento = prazo_pagamento
        self.plano_contas = plano_contas
        self.descricao = descricao

    def __str__(self):
        return f"Fornecedor(id={self.id_fornecedor}, nome={self.nome_fornecedor}, prazo_pagamento={self.prazo_pagamento}, plano_contas={self.plano_contas}, descricao={self.descricao})"
