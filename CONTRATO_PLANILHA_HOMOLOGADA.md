# Contrato da planilha homologada

Versão: `1.0`

`saida.xlsx` é o único arquivo que futuramente poderá ser entregue ao robô. Ele só é atualizado quando a execução termina com status **HOMOLOGADO**.

## Colunas e regras

| Coluna | Regra |
| --- | --- |
| `LOJA`, `FORNECEDOR`, `PLANO_CONTAS`, `BANCO` | Obrigatórias e não vazias. |
| `DESCRICAO` | Texto livre. |
| `DATA_VENCIMENTO`, `DATA_EMISSAO` | Obrigatórias no formato `DD/MM/AAAA`; emissão não pode ser posterior ao vencimento. |
| `DATA_PAGAMENTO` | Opcional; quando preenchida, usa `DD/MM/AAAA`. |
| `VALOR`, `VALOR_JUROS`, `VALOR_DESCONTO` | Números finitos maiores ou iguais a zero. |

## Estados da revisão

- `APROVADO`: pode compor a saída homologada.
- `PENDENTE_CADASTRO`: bloqueia a saída operacional se a loja estiver ativa.
- `FORA_DA_EXPORTACAO`: permanece no `preview.xlsx`, mas não entra na saída operacional.
- `ERRO_DE_PROCESSAMENTO`: bloqueia a saída operacional.

O arquivo `preview.xlsx` sempre é gerado para revisão. Cada execução acrescenta um registro a `historico_execucoes.jsonl`, incluindo o hash SHA-256 da planilha de entrada e o resultado da homologação.
