# Lojas que existem na planilha mas NAO devem ir pro arquivo final
# exportado (ex: ainda nao sao lancadas na plataforma de contas a pagar).
# Usa o nome da loja ja resolvido (o mesmo que aparece na coluna LOJA
# do arquivo de saida), nao o codigo bruto da planilha de entrada.
ARQUIVO_ENTRADA = "entrada.xlsx"
ARQUIVO_SAIDA = "saida.xlsx"
ARQUIVO_PREVIEW = "preview.xlsx"
COLUNAS_OBRIGATORIAS = {"LOJA", "NF", "VLR", "ORIGEM", "VENC"}
LIMITE_EXEMPLOS = 5
MARCADOR_PENDENCIA = "DESCONHECID"
