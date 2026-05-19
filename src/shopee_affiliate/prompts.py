from pathlib import Path

from shopee_affiliate.config import get_settings


class PromptStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or get_settings().prompt_dir

    def load(self, agent: str, name: str) -> str:
        path = self.root / agent / name
        if not path.exists():
            raise FileNotFoundError(f"Prompt not found: {path}")
        return path.read_text(encoding="utf-8")

