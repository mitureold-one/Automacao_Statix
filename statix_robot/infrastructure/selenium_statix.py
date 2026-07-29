"""Adaptador Selenium para o Statix, isolado das regras de planilha."""

import os
import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from urllib.parse import urlparse

from statix_robot.domain.plataforma import StatusPlataforma
from statix_robot.infrastructure.configuracao_privada import carregar_configuracao_robo


@dataclass(frozen=True)
class CredenciaisStatix:
    usuario: str
    senha: str
    url: str

    @classmethod
    def do_ambiente(cls):
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ModuleNotFoundError:
            pass
        usuario = os.getenv("STATIX_USUARIO")
        senha = os.getenv("STATIX_SENHA")
        url = os.getenv("STATIX_URL")
        if not usuario or not senha or not url:
            raise EnvironmentError(
                "Defina STATIX_USUARIO, STATIX_SENHA e STATIX_URL no ambiente "
                "antes da execução real."
            )
        return cls(usuario=usuario, senha=senha, url=url.rstrip("/"))


def classificar_correspondencias(correspondencias: list[dict]) -> StatusPlataforma:
    """Decisão pura e testável para os resultados da pesquisa na plataforma."""
    if not correspondencias:
        return StatusPlataforma.NAO_ENCONTRADO
    if len(correspondencias) > 1:
        return StatusPlataforma.DUPLICATA
    status = correspondencias[0]["status"].upper()
    if status == "PAGO":
        return StatusPlataforma.PAGO
    return StatusPlataforma.PENDENTE


class SeleniumStatix:
    def __init__(
        self,
        credenciais: CredenciaisStatix,
        timeout: int = 15,
        normalizacoes: dict[str, str] | None = None,
    ):
        self.credenciais = credenciais
        self.timeout = timeout
        self.driver = None
        self.wait = None
        self.By = self.Keys = self.EC = self.TimeoutException = None
        self.diagnostico_pagamento = {}
        self.normalizacoes = normalizacoes or {}

    @classmethod
    def do_ambiente(cls, timeout: int = 15):
        configuracao = carregar_configuracao_robo()
        return cls(CredenciaisStatix.do_ambiente(), timeout, configuracao.normalizacoes)

    def _normalizar_privado(self, valor: str) -> str:
        texto = str(valor).upper()
        for origem, destino in self.normalizacoes.items():
            texto = texto.replace(origem, destino)
        return texto

    def conectar(self, abrir_despesas: bool = True) -> None:
        try:
            from selenium import webdriver
            from selenium.common.exceptions import TimeoutException
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            from selenium.webdriver.common.keys import Keys
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.support.ui import WebDriverWait
        except ModuleNotFoundError as exc:
            raise RuntimeError("Selenium não está instalado. Instale requirements.txt antes de executar o robô real.") from exc

        options = Options()
        options.add_experimental_option("detach", False)
        options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
        self.driver = webdriver.Chrome(options=options)
        self.driver.maximize_window()
        self.wait = WebDriverWait(self.driver, self.timeout)
        self.By, self.Keys, self.EC, self.TimeoutException = By, Keys, EC, TimeoutException

        self.driver.get(f"{self.credenciais.url}/login")
        self.wait.until(self.EC.element_to_be_clickable((self.By.NAME, "login"))).send_keys(self.credenciais.usuario)
        self.driver.find_element(self.By.NAME, "senha").send_keys(self.credenciais.senha)
        self._click(self.driver.find_element(self.By.XPATH, "//button[@type='submit']"))
        self.wait.until(self.EC.url_changes(f"{self.credenciais.url}/login"))
        if "login" in self.driver.current_url.lower():
            raise ValueError("Login falhou; verifique as credenciais.")
        if abrir_despesas:
            self._abrir_despesas()

    def fechar(self) -> None:
        if self.driver:
            self.driver.quit()
            self.driver = self.wait = None

    def requisicoes_api(self) -> list[dict]:
        """Retorna somente método e rota, sem expor credenciais ou cabeçalhos."""
        self._garantir_conexao()
        requisicoes = []
        vistos = set()
        for registro in self.driver.get_log("performance"):
            try:
                mensagem = json.loads(registro["message"])["message"]
                if mensagem["method"] != "Network.requestWillBeSent":
                    continue
                requisicao = mensagem["params"]["request"]
                url = requisicao["url"]
                if urlparse(url).netloc != urlparse(self.credenciais.url).netloc:
                    continue
                rota = url.split("?", 1)[0]
                chave = (requisicao["method"], rota)
                if chave not in vistos:
                    vistos.add(chave)
                    requisicoes.append({"metodo": requisicao["method"], "rota": rota})
            except (KeyError, TypeError, ValueError):
                continue
        return requisicoes

    def detalhes_da_ultima_requisicao(self, trecho_rota: str) -> tuple[str, dict]:
        """Obtém corpo e cabeçalhos de sessão, sem exibi-los ou persistir."""
        self._garantir_conexao()
        corpo, cabecalhos = None, {}
        for registro in self.driver.get_log("performance"):
            try:
                mensagem = json.loads(registro["message"])["message"]
                if mensagem["method"] != "Network.requestWillBeSent":
                    continue
                requisicao = mensagem["params"]["request"]
                if trecho_rota in requisicao["url"] and requisicao["method"] == "POST":
                    corpo = requisicao.get("postData")
                    cabecalhos = {
                        nome: valor for nome, valor in requisicao.get("headers", {}).items()
                        if nome.lower() == "authorization" or nome.lower().startswith("x-")
                    }
            except (KeyError, TypeError, ValueError):
                continue
        if not corpo:
            raise RuntimeError(f"Não foi possível localizar o corpo da requisição: {trecho_rota}")
        return corpo, cabecalhos

    def repetir_consulta_api(self, rota: str, corpo: str, cabecalhos: dict) -> dict:
        """Executa uma consulta POST direta no contexto autenticado do navegador."""
        self._garantir_conexao()
        return self.driver.execute_async_script(
            """
            const done = arguments[arguments.length - 1];
            fetch(arguments[0], {
                method: 'POST',
                credentials: 'same-origin',
                headers: {...arguments[2], 'Content-Type': 'application/json'},
                body: arguments[1],
            }).then(async response => {
                const body = await response.text();
                done({status: response.status, tamanhoResposta: body.length, corpo: body});
            }).catch(error => done({erro: String(error)}));
            """,
            rota,
            corpo,
            cabecalhos,
        )

    def _garantir_conexao(self):
        if not self.driver or not self.wait:
            raise RuntimeError("Selenium não conectado. Chame conectar() antes de operar.")

    def _click(self, elemento) -> None:
        self.driver.execute_script("arguments[0].click();", elemento)

    def _abrir_despesas(self) -> None:
        self._garantir_conexao()
        # A estrutura do menu lateral muda com frequência. A rota é estável e
        # a sessão autenticada continua sendo exigida pelo servidor.
        self.driver.get(f"{self.credenciais.url}/management/expenses")
        self._pronto("//input[@placeholder='Selecione os status']")

    def _pronto(self, xpath: str):
        self._garantir_conexao()
        try:
            self.wait.until(self.EC.invisibility_of_element_located((self.By.CSS_SELECTOR, "div.MuiBackdrop-root")))
        except Exception:
            pass
        return self.wait.until(self.EC.element_to_be_clickable((self.By.XPATH, xpath)))

    def _digitar_data(self, campo, data: str) -> None:
        campo.click()
        campo.send_keys(self.Keys.CONTROL + "a")
        campo.send_keys(self.Keys.DELETE)
        for digito in data.replace("/", ""):
            campo.send_keys(digito)
        valor_exibido = campo.get_attribute("value").strip()
        if valor_exibido != data:
            raise ValueError(
                f"Data nao confirmada no campo: esperado {data}, exibido {valor_exibido or '[vazio]'}."
            )

    def _autocomplete(self, xpath: str, valor: str, limpar: bool = True) -> None:
        campo = self._pronto(xpath)
        campo.click()
        if limpar:
            campo.send_keys(self.Keys.CONTROL + "a")
            campo.send_keys(self.Keys.BACKSPACE)
        texto = str(valor).strip()
        # O seletor de planos pesquisa pelo codigo ("7.2"), mas nao pelo
        # nome completo. O nome completo continua sendo validado abaixo.
        busca = texto
        eh_plano_contas = "planos de contas" in xpath.lower()
        eh_fornecedor = "fornecedor" in xpath.lower()
        if eh_plano_contas:
            codigo = re.match(r"^\s*([0-9.]+)", texto)
            busca = codigo.group(1) if codigo else texto
        elif eh_fornecedor:
            busca = " ".join(self._normalizar_privado(texto).split()[:3])
        campo.send_keys(busca)
        opcoes = self.wait.until(self.EC.presence_of_all_elements_located((
            self.By.XPATH, "//ul[contains(@class,'MuiAutocomplete-listbox')]/li"
        )))
        if not opcoes:
            raise ValueError(f"Nenhuma opção encontrada para: {valor}")
        if eh_fornecedor:
            normalizar = lambda conteudo: re.sub(
                r"[^A-Z0-9]", "", self._normalizar_privado(conteudo)
            )
            alvo = normalizar(texto)
            opcao = next(
                (item for item in opcoes if alvo in normalizar(item.text) or normalizar(item.text) in alvo),
                opcoes[0],
            )
            self._click(opcao)
            return
        if not eh_plano_contas:
            self._click(opcoes[0])
            return
        normalizar = lambda conteudo: re.sub(r"\s+", " ", str(conteudo).strip().casefold())
        opcao = next((item for item in opcoes if normalizar(item.text) == normalizar(texto)), None)
        if opcao is None:
            raise ValueError(f"Plano de contas exato nao encontrado para: {valor}")
        self._click(opcao)

    @staticmethod
    def _moeda(valor: float) -> str:
        return f"{float(valor):.2f}".replace(".", ",")

    @staticmethod
    def _periodo(dados: dict) -> tuple[str, str]:
        datas = []
        for chave in ("DATA_EMISSAO", "DATA_VENCIMENTO", "DATA_PAGAMENTO"):
            try:
                datas.append(datetime.strptime(str(dados.get(chave, "")), "%d/%m/%Y"))
            except ValueError:
                pass
        if not datas:
            hoje = datetime.now()
            return ((hoje - timedelta(days=365 * 5)).strftime("%d/%m/%Y"), (hoje + timedelta(days=365 * 2)).strftime("%d/%m/%Y"))
        return ((min(datas) - timedelta(days=30)).strftime("%d/%m/%Y"), (max(datas) + timedelta(days=30)).strftime("%d/%m/%Y"))

    def _filtrar(self, dados: dict, status: list[str]) -> list:
        self.driver.get(f"{self.credenciais.url}/management/expenses")
        self._pronto("//input[@placeholder='Selecione os status']")
        campo_status = self._pronto("//input[@placeholder='Selecione os status']")
        self._click(campo_status)
        for _ in range(5):
            campo_status.send_keys(self.Keys.BACKSPACE)
        time.sleep(0.5)
        for indice, nome in enumerate(status):
            self._autocomplete("//input[@placeholder='Selecione os status']", nome, limpar=indice == 0)
        self._autocomplete("//input[@placeholder='Selecione as lojas']", dados["LOJA"])
        self._autocomplete("//input[@placeholder='Selecione os fornecedores']", dados["FORNECEDOR"])
        inicio, fim = self._periodo(dados)
        campos = self.wait.until(self.EC.presence_of_all_elements_located((self.By.XPATH, "//input[@placeholder='DD/MM/YYYY']")))
        self._digitar_data(campos[0], inicio)
        self._digitar_data(campos[1], fim)
        self._click(self._pronto("//button[contains(.,'Pesquisar')]"))
        limite = time.monotonic() + min(self.timeout, 15)
        while time.monotonic() < limite:
            linhas = self.driver.find_elements(self.By.XPATH, "//tbody/tr")
            if linhas:
                return linhas
            corpo = self.driver.find_element(self.By.TAG_NAME, "body").text.lower()
            if any(texto in corpo for texto in ("nenhum resultado", "sem registros", "no records")):
                return []
            time.sleep(0.4)
        return []

    def verificar(self, dados: dict) -> StatusPlataforma:
        linhas = self._filtrar(dados, ["Pendente", "Pago"])
        valores = self._valores_da_grade(dados)
        data_emissao = dados["DATA_EMISSAO"]
        correspondencias = []
        for linha in linhas:
            celulas = linha.find_elements(self.By.XPATH, "./td")
            texto = linha.text
            if len(celulas) >= 8 and celulas[0].text.strip() == data_emissao and any(valor in texto for valor in valores):
                correspondencias.append({"status": "PAGO" if "Pago" in texto else "PENDENTE"})
        return classificar_correspondencias(correspondencias)

    def consultar_linhas(self, dados: dict) -> list[list[str]]:
        """Consulta linhas por filtros, sem efetuar qualquer operação financeira."""
        linhas = self._filtrar(dados, ["Pendente", "Pago"])
        return [[celula.text.strip() for celula in linha.find_elements(self.By.XPATH, "./td")] for linha in linhas]

    def estornar(self, dados: dict) -> None:
        """Estorna uma despesa paga localizada por filtros estritos."""
        linhas = self._filtrar(dados, ["Pago"])
        valores = self._valores_da_grade(dados)
        candidatas = [
            linha for linha in linhas
            if dados["DATA_EMISSAO"] in linha.text
            and any(valor in linha.text for valor in valores)
            and (not dados.get("PLANO_ATUAL") or dados["PLANO_ATUAL"] in linha.text)
        ]
        if len(candidatas) != 1:
            raise ValueError(
                f"Estorno bloqueado: esperava uma unica despesa paga; encontradas: {len(candidatas)}."
            )
        alvo = candidatas[0]
        self._click(alvo.find_element(self.By.XPATH, ".//button[@title='Detalhar' or @aria-label='Detalhar']"))
        self._click(self._pronto("//button[normalize-space()='Estornar']"))
        self._click(self._pronto("//button[normalize-space()='ESTORNAR']"))
        self.wait.until(self.EC.invisibility_of_element_located((self.By.XPATH, "//button[normalize-space()='ESTORNAR']")))

    def lancar(self, dados: dict) -> None:
        self._click(self._pronto("//button[contains(.,'Nova Despesa')]"))
        self._autocomplete("//input[@placeholder='Selecione as lojas']", dados["LOJA"])
        self._autocomplete("//input[@placeholder='Selecione os fornecedor']", dados["FORNECEDOR"])
        self._autocomplete("//input[@placeholder='Selecione os planos de contas']", dados["PLANO_CONTAS"])
        campo_valor = self._pronto("//input[contains(@value,'R$')]")
        campo_valor.send_keys(self.Keys.CONTROL + "a")
        campo_valor.send_keys(self._moeda(dados["VALOR"]))
        datas = self.wait.until(self.EC.presence_of_all_elements_located((self.By.XPATH, "//input[@placeholder='DD/MM/YYYY']")))
        self._digitar_data(datas[0], dados["DATA_EMISSAO"])
        self._digitar_data(datas[1], dados["DATA_VENCIMENTO"])
        self._pronto("//input[@placeholder='Insira a descrição da despesa']").send_keys(dados["DESCRICAO"])
        self._autocomplete("//input[@placeholder='Selecione a conta bancária']", dados["BANCO"])
        self._click(self._pronto("//button[contains(.,'Lançar Despesa')]"))
        self._confirmar_modal()

    def pagar(self, dados: dict) -> None:
        linhas = self._filtrar(dados, ["Pendente"])
        valores = self._valores_da_grade(dados)
        candidatas = [
            linha for linha in linhas
            if dados["DATA_EMISSAO"] in linha.text and any(valor in linha.text for valor in valores)
        ]
        alvo = candidatas[0] if len(candidatas) == 1 else None
        if alvo is None:
            raise ValueError(f"Despesa pendente não encontrada para pagamento: {dados['FORNECEDOR']}")
        self._click(alvo.find_element(self.By.XPATH, ".//button[@title='Detalhar' or @aria-label='Detalhar']"))
        campo_data = self._pronto("//legend[contains(.,'Data de Pagamento')]/ancestor::div[contains(@class,'MuiInputBase-root')]//input")
        self._digitar_data(campo_data, dados["DATA_PAGAMENTO"])
        self._preencher_moeda("//label[contains(text(),'Juros')]/following-sibling::div//input", dados["VALOR_JUROS"])
        self._preencher_moeda("//label[contains(text(),'Desconto')]/following-sibling::div//input", dados["VALOR_DESCONTO"])
        self._click(self._pronto("//button[contains(@class,'MuiButton-containedPrimary') and contains(.,'Liquidar')]"))
        self._confirmar_modal()
        self._capturar_diagnostico_pagamento()

    def confirmar_estorno(self, dados: dict) -> None:
        """Garante que o item estornado realmente aparece com o novo status."""
        linhas = self._filtrar(dados, ["Estornado"])
        valores = self._valores_da_grade(dados)
        encontradas = [
            linha for linha in linhas
            if dados["DATA_EMISSAO"] in linha.text
            and any(valor in linha.text for valor in valores)
            and (not dados.get("PLANO_ATUAL") or dados["PLANO_ATUAL"] in linha.text)
        ]
        if len(encontradas) != 1:
            raise ValueError(f"Validacao de estorno bloqueada: encontradas {len(encontradas)} despesa(s) correspondente(s).")

    def _valores_da_grade(self, dados: dict) -> set[str]:
        valor_original = float(dados["VALOR"])
        valor_total = valor_original + float(dados.get("VALOR_JUROS", 0)) - float(dados.get("VALOR_DESCONTO", 0))
        valores = set()
        for valor in (valor_original, valor_total):
            valores.add(self._moeda(valor))
            valores.add(f"{valor:,.2f}".replace(",", "#").replace(".", ",").replace("#", "."))
        return valores

    def _capturar_diagnostico_pagamento(self) -> None:
        """Extrai somente campos de data da ultima chamada de pagamento."""
        try:
            corpo, _ = self.detalhes_da_ultima_requisicao("/payables/")
            carga = json.loads(corpo)
            self.diagnostico_pagamento = {
                chave: valor for chave, valor in carga.items()
                if "date" in chave.lower() or "data" in chave.lower()
            }
            if self.diagnostico_pagamento:
                print(f"[DIAGNOSTICO] Datas enviadas ao Statix: {self.diagnostico_pagamento}")
        except Exception:
            self.diagnostico_pagamento = {}

    def confirmar_pagamento(self, dados: dict, aceitar_mais_um_dia: bool = False) -> None:
        """Confere no grid o pagamento efetivamente gravado pelo Statix."""
        linhas = self._filtrar(dados, ["Pago"])
        valores = self._valores_da_grade(dados)
        candidatas = [
            linha for linha in linhas
            if dados["DATA_EMISSAO"] in linha.text and any(valor in linha.text for valor in valores)
        ]
        if len(candidatas) != 1:
            raise ValueError(
                f"Validacao de pagamento bloqueada: esperava uma unica despesa paga; encontradas: {len(candidatas)}."
            )
        celulas = candidatas[0].find_elements(self.By.XPATH, "./td")
        data_exibida = celulas[2].text.strip() if len(celulas) > 2 else ""
        if data_exibida != dados["DATA_PAGAMENTO"]:
            esperado = datetime.strptime(dados["DATA_PAGAMENTO"], "%d/%m/%Y")
            exibido = datetime.strptime(data_exibida, "%d/%m/%Y")
            if aceitar_mais_um_dia and abs(exibido - esperado) == timedelta(days=1):
                print(f"[AVISO] Statix gravou pagamento em {data_exibida}; diferenca de 1 dia aceita explicitamente.")
                return
            raise ValueError(
                f"Pagamento divergente: esperado {dados['DATA_PAGAMENTO']}, Statix exibiu {data_exibida}."
            )

    def _preencher_moeda(self, xpath: str, valor: float) -> None:
        campo = self._pronto(xpath)
        self.driver.execute_script("arguments[0].value = '';", campo)
        campo.send_keys(self._moeda(valor))

    def _confirmar_modal(self) -> None:
        self._click(self._pronto("//button[normalize-space()='Confirmar' or contains(.,'Confirmar')]"))
        self.wait.until(self.EC.invisibility_of_element_located((self.By.CSS_SELECTOR, "div.MuiModal-root")))
