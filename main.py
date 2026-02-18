import os
from pathlib import Path

_env_file = Path(__file__).resolve().parent / ".env"
if _env_file.is_file():
    for line in _env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())

from app.ui.main_window import run_app


if __name__ == "__main__":
    run_app()
