"""Run explicitly with Windows-native Python against a disposable migrated DB."""

from __future__ import annotations

import re
from datetime import timedelta
from pathlib import Path

from tests.backend.reviewer_test_support import Authenticator, Clock
from tests.backend.test_authority_decision_engine import EVALUATED_AT, _kr_harness, _kr_request
from tests.backend.test_reviewer_runtime import enroll

from toss_dashboard_api.reviewer import windows_owner
from toss_dashboard_api.reviewer.issuer_disposition import IssuerDispositionService
from toss_dashboard_api.reviewer.runtime import _Runtime

pytest_plugins = ("tests.backend.conftest",)


def test_b2d_entry_uses_real_win32_owner_and_token_user(
    database_context, workspace_tmp_path: Path
) -> None:
    harness = _kr_harness(database_context)
    ready = harness.engine.evaluate(_kr_request(harness))
    checked: list[str] = []

    def actual_owner() -> str:
        result = windows_owner._verify_directory(
            workspace_tmp_path.resolve(), windows_owner._Win32()
        )
        checked.append(result)
        return result

    runtime = _Runtime(
        database_context.engine, actual_owner, Clock(EVALUATED_AT + timedelta(minutes=1))
    )
    authenticator = Authenticator()
    enroll(runtime, authenticator)
    service = IssuerDispositionService(runtime, harness.engine)
    challenge = service.issue(ready.decision.issuer_decision_id, "APPROVED")
    result = service.complete(
        challenge.challenge_id,
        authenticator.assertion(challenge.options, 9),
        structured_reason_code="VERIFIED_EXACT_AUTHORITY",
        review_note="Windows owner boundary probe",
    )
    assert result.approval_event_id.startswith("iap_")
    assert len(checked) >= 2
    assert len(set(checked)) == 1
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", checked[0])
