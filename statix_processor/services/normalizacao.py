"""Normalização dos dados brutos da planilha."""

import re
import unicodedata

import pandas as pd


class Normalizador_Lancamentos:
    def limpar_texto(self, texto) -> str:
        """
        Sanitização completa: remove acentos, caracteres especiais,
        quebras de linha e padroniza em MAIÚSCULO.
        """
        if texto is None or str(texto).lower() == "nan":
            return ""

        texto = str(texto).strip().upper()

        texto = "".join(
            caractere for caractere in unicodedata.normalize("NFD", texto)
            if unicodedata.category(caractere) != "Mn"
        )

        texto = re.sub(r"[^A-Z0-9\s]", "", texto)
        texto = re.sub(r"\s+", " ", texto).strip()

        return texto

    def normalizar(self, df):
        df = df.copy()

        df.columns = [self.limpar_texto(coluna) for coluna in df.columns]

        for coluna in df.select_dtypes(include=["object", "string"]).columns:
            df[coluna] = df[coluna].apply(self.limpar_texto)

        df = df.loc[:, df.columns != ""]
        df = df.replace("", pd.NA).dropna(axis=1, how="all")

        return df
