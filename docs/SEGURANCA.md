# Segurança e publicação

## O que não deve ser versionado

- `.env` e quaisquer credenciais;
- `config/negocio.json`;
- planilhas reais (`.xlsx`, `.xls` e `.csv`);
- históricos, auditorias e arquivos de progresso;
- ambientes virtuais, caches e logs.

O arquivo privado também contém os filtros operacionais do Selenium. Nunca
copie esses valores para `config/negocio.example.json`.

## Antes de publicar

1. Confirme que somente `config/negocio.example.json` contém dados fictícios.
2. Execute `git status --ignored` e revise todos os arquivos.
3. Procure nomes, contas, e-mails, documentos, URLs privadas e segredos no
   conteúdo que será enviado.
4. Execute os testes.
5. Faça o primeiro commit somente após essa revisão.

Se credenciais ou dados privados já foram commitados, adicionar o arquivo ao
`.gitignore` não basta. Revogue e substitua as credenciais, remova os dados de
todo o histórico com uma ferramenta apropriada e só então publique novamente.

Não envie os arquivos privados para issues, pull requests, logs de CI ou
artefatos de teste.
