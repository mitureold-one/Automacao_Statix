# AUTOMAÇÂO DO STATIX

Processador de planilhas e robô de automação para lançamentos de contas a
pagar. O projeto separa a transformação dos dados da automação no navegador e
mantém credenciais e cadastros do negócio fora do código-fonte.

## Requisitos

- Python 3.11 ou superior
- Google Chrome, somente para a automação real

## Instalação

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
Copy-Item config\negocio.example.json config\negocio.json
```

Preencha `.env` com as credenciais e `config/negocio.json` com os cadastros e
regras do ambiente. Esses dois arquivos são privados e ignorados pelo Git.

## Uso

Coloque a planilha privada em `entrada.xlsx` e execute:

```powershell
python main.py
```

O processador gera `preview.xlsx` para revisão. Somente quando não há bloqueios
ele atualiza `saida.xlsx`, arquivo homologado consumido pelo robô.

Para simular o robô sem alterar o sistema:

```powershell
python robot.py
```

Para ver todas as opções:

```powershell
python robot.py --help
```

As opções de execução real exigem confirmação explícita. Revise a simulação e
os arquivos de saída antes de utilizá-las.

## Testes

```powershell
python -m unittest discover -s tests
```

Os testes usam exclusivamente dados fictícios de
`config/negocio.example.json`.

## Configuração

As variáveis aceitas estão em `.env.example`. O caminho do arquivo privado de
negócio pode ser alterado com `STATIX_CONFIG_NEGOCIO`.

Consulte:

- [Arquitetura](docs/ARQUITETURA.md)
- [Configuração privada](docs/CONFIGURACAO.md)
- [Segurança e publicação](docs/SEGURANCA.md)

## Aviso

Este é um projeto pessoal que desenvolvi para resolver um problema do mundo real enfrentado por um amigo. Ele visa otimizar a rotina diária dele e tornar o processo muito mais fácil
