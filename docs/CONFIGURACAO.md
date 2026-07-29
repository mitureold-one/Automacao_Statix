# Configuração privada

## Credenciais

Crie `.env` a partir de `.env.example`:

```dotenv
STATIX_USUARIO=
STATIX_SENHA=
STATIX_URL=
STATIX_CONFIG_NEGOCIO=config/negocio.json
```

Nunca preencha `.env.example` com valores reais.

## Cadastros e regras

Copie `config/negocio.example.json` para `config/negocio.json`. O arquivo
privado reúne:

- lojas, contas bancárias e colaboradores vinculados;
- fornecedores, prazos, planos de contas e descrições;
- regras baseadas no texto da nota;
- exceções por loja e nota;
- lojas excluídas da exportação operacional.

O exemplo versionado é fictício e também funciona como referência do formato.
O processador encerra com uma mensagem clara quando o arquivo privado não
existe ou contém JSON inválido.

A seção `robo` do mesmo arquivo mantém fora do código:

- equivalências privadas usadas na busca de fornecedores;
- critérios da consulta histórica;
- período, plano e fornecedor selecionados para auditoria;
- nome do relatório de auditoria;
- justificativa usada na prévia de estorno.

A URL da plataforma deve ser informada em `STATIX_URL`; o código não contém
domínio padrão. Os comandos públicos são genéricos: `--consultar-historico` e
`--auditar`.

Para usar outro local, defina `STATIX_CONFIG_NEGOCIO` com o caminho desejado.
Em produção, prefira um arquivo fora da pasta clonada, protegido pelas
permissões do sistema operacional.
