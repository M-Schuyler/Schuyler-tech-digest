from __future__ import annotations

from main import parse_args


def test_monitor_scan_command_accepts_now_override(monkeypatch) -> None:
    monkeypatch.setattr("sys.argv", ["main.py", "monitor-scan", "--now", "2026-04-24T00:00:00+00:00"])

    args = parse_args()

    assert args.command == "monitor-scan"
    assert args.now == "2026-04-24T00:00:00+00:00"
