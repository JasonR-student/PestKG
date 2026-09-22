from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
API_SRC = ROOT / "apps" / "api" / "src"
OUTPUT = Path(__file__).resolve().with_name("openapi-v1.1.json")

sys.path.insert(0, str(API_SRC))

from pestkg_api.main import app  # noqa: E402


def main() -> None:
    OUTPUT.write_text(
        json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
