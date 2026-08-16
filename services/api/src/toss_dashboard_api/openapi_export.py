from __future__ import annotations

import argparse
import json
from pathlib import Path

from toss_dashboard_api.main import app


def export_openapi(output: Path) -> None:
    rendered = json.dumps(app.openapi(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Export deterministic FastAPI OpenAPI schema")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    export_openapi(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
