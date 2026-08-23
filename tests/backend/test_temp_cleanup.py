from pathlib import Path

import pytest
from tests.backend.conftest import (
    PROJECT_ROOT,
    _remove_workspace_test_path,
    managed_workspace_test_directory,
)


def test_managed_workspace_test_directory_is_removed_after_use() -> None:
    with managed_workspace_test_directory() as path:
        sentinel = path / "sentinel.txt"
        sentinel.touch()
        assert sentinel.exists()
    assert not path.exists()


def test_workspace_cleanup_rejects_targets_outside_validated_base() -> None:
    unsafe_target = Path(PROJECT_ROOT / "var").resolve()
    with pytest.raises(RuntimeError, match="escaped"):
        _remove_workspace_test_path(unsafe_target)
