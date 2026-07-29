# Arquitetura

O projeto é dividido em dois pacotes:

| Componente | Responsabilidade |
| --- | --- |
| `statix_processor` | Lê, normaliza, transforma, revisa e homologa a planilha. |
| `statix_robot` | Consome somente a saída homologada e automatiza a plataforma. |

Dentro do processador:

| Camada | Responsabilidade |
| --- | --- |
| `application` | Coordena o caso de uso completo. |
| `domain` | Define os modelos e o contrato operacional. |
| `services` | Aplica normalização e transformação. |
| `infrastructure` | Integra Excel, histórico e configuração privada. |

## Fluxo

`entrada.xlsx` → processador → `preview.xlsx` → homologação → `saida.xlsx` → robô

As regras e os cadastros privados entram no processador por
`config/negocio.json`. O robô não importa regras da planilha bruta e não deve
processar um arquivo que viole o contrato homologado.
