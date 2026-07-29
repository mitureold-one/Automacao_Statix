import json
from datetime import datetime
from pathlib import Path


class RepositorioProgresso:
    def __init__(self, caminho: Path):
        self.caminho = caminho

    def carregar(self) -> dict:
        if not self.caminho.exists():
            return {"concluidos": [], "erros": {}}
        try:
            dados = json.loads(self.caminho.read_text(encoding="utf-8"))
            return {"concluidos": dados.get("concluidos", []), "erros": dados.get("erros", {})}
        except (json.JSONDecodeError, OSError):
            return {"concluidos": [], "erros": {}}

    def salvar(self, progresso: dict) -> None:
        self.caminho.write_text(json.dumps(progresso, ensure_ascii=False, indent=2), encoding="utf-8")

    def registrar_sucesso(self, progresso: dict, indice: int, rotulo: str) -> None:
        progresso["concluidos"].append({"idx": indice, "label": rotulo, "em": datetime.now().isoformat(timespec="seconds")})
        self.salvar(progresso)

    def registrar_erro(self, progresso: dict, indice: int, rotulo: str, motivo: str) -> None:
        progresso["erros"][str(indice)] = {"label": rotulo, "motivo": motivo, "em": datetime.now().isoformat(timespec="seconds")}
        self.salvar(progresso)
