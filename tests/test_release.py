from pathlib import Path

from scripts.check_release import check_release


def test_release_check_passes_for_repository() -> None:
    root = Path(__file__).resolve().parents[1]
    assert check_release(root) == []
