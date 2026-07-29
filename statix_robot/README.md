# Robô Statix

O robô consome exclusivamente `saida.xlsx` já homologada pelo processador.

Nesta etapa, `robot.py` executa apenas uma simulação: valida a planilha, percorre o lote e aplica as mesmas decisões do robô antigo sem abrir navegador, gravar progresso ou alterar o sistema Statix.

A futura integração Selenium será um adaptador de `PlataformaContasAPagar`. Ela não poderá importar regras de planilha, nem aceitar arquivos que não atendam ao contrato de homologação.
