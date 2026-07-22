import json
import subprocess
import sys
from pathlib import Path


def run_cli(database: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "sample_app.cli",
            "--database",
            str(database),
            *arguments,
        ],
        capture_output=True,
        check=False,
        text=True,
    )


def test_cli_persists_create_get_and_list_across_processes(tmp_path: Path) -> None:
    database = tmp_path / "orders.sqlite3"

    created = run_cli(database, "create", "--id", "order-2", "--item", "cable", "--quantity", "3")
    assert created.returncode == 0
    assert json.loads(created.stdout) == {"item": "cable", "order_id": "order-2", "quantity": 3}

    run_cli(database, "create", "--id", "order-1", "--item", "adapter", "--quantity", "1")
    retrieved = run_cli(database, "get", "--id", "order-2")
    listed = run_cli(database, "list")

    assert json.loads(retrieved.stdout) == json.loads(created.stdout)
    assert [order["order_id"] for order in json.loads(listed.stdout)] == ["order-1", "order-2"]


def test_cli_reports_invalid_missing_and_duplicate_orders(tmp_path: Path) -> None:
    database = tmp_path / "orders.sqlite3"

    invalid = run_cli(database, "create", "--id", "bad", "--item", "widget", "--quantity", "0")
    missing = run_cli(database, "get", "--id", "missing")
    run_cli(database, "create", "--id", "same", "--item", "widget", "--quantity", "1")
    duplicate = run_cli(database, "create", "--id", "same", "--item", "other", "--quantity", "2")

    assert invalid.returncode == missing.returncode == duplicate.returncode == 1
    assert "quantity must be a positive integer" in invalid.stderr
    assert "order not found: missing" in missing.stderr
    assert "order already exists: same" in duplicate.stderr
