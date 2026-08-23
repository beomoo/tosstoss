from __future__ import annotations

import os

from toss_dashboard_api.main import create_app

app = create_app()


@app.get("/_test/unhandled/{probe}")
def raise_unhandled(probe: str) -> None:
    del probe
    raise RuntimeError(os.environ["UVICORN_TEST_EXCEPTION"])
