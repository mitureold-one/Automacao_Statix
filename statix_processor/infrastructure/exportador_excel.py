from dataclasses import asdict, is_dataclass

import pandas as pd


class Exportador_Excel:
    def __init__(self, arquivo: str):
        self.arquivo = arquivo

    def _para_dataframe(self, dados) -> pd.DataFrame:
        if isinstance(dados, pd.DataFrame):
            return dados

        linhas = []
        for item in dados:
            if is_dataclass(item):
                linhas.append(asdict(item))
            elif hasattr(item, "__dict__"):
                linhas.append(vars(item))
            else:
                linhas.append(item)

        return pd.DataFrame(linhas)

    def exportar_dados(self, dados):
        df = self._para_dataframe(dados)
        destino = str(self.arquivo)
        extensao = destino.lower().rsplit(".", 1)[-1] if "." in destino else ""

        if extensao == "xls":
            try:
                df.to_excel(destino, index=False, engine="xlwt")
            except ModuleNotFoundError as exc:
                raise RuntimeError(
                    "Para exportar em .xls, instale o pacote 'xlwt' (pip install xlwt)."
                ) from exc
            return destino

        df.to_excel(destino, index=False)
        return destino

