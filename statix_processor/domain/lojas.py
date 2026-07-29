class Loja:
    def __init__(self, id_loja, nome_loja, conta_banco, funcionario=None):
        self.id_loja = id_loja
        self.nome_loja = nome_loja
        self.conta_banco = conta_banco
        self.funcionario = funcionario

    def __str__(self):
        return f"Loja(id={self.id_loja}, nome={self.nome_loja}, conta_banco={self.conta_banco}, funcionario={self.funcionario})"
