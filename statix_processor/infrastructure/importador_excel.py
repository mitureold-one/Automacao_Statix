import pandas as pd

class Importador_Excel:

    def importar(self, caminho: str) -> pd.DataFrame:
        return pd.read_excel(caminho)
