from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"


def read_workflow(name: str) -> str:
    return (WORKFLOWS_DIR / name).read_text(encoding="utf-8")


def test_intraday_and_close_workflows_expose_manual_run_time_override() -> None:
    intraday = read_workflow("intraday-market-scan.yml")
    close = read_workflow("market-close-alert.yml")

    assert "workflow_dispatch:\n    inputs:\n      run_at:" in intraday
    assert "workflow_dispatch:\n    inputs:\n      run_at:" in close
    assert "--now" in intraday
    assert "--now" in close


def test_workflows_opt_in_to_node24_runtime() -> None:
    for workflow_name in (
        "daily-ai-market-brief.yml",
        "intraday-market-scan.yml",
        "market-close-alert.yml",
    ):
        workflow = read_workflow(workflow_name)
        assert "FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: \"true\"" in workflow


def test_workflows_use_node24_capable_action_versions() -> None:
    intraday = read_workflow("intraday-market-scan.yml")
    close = read_workflow("market-close-alert.yml")
    daily = read_workflow("daily-ai-market-brief.yml")

    for workflow in (intraday, close, daily):
        assert "uses: actions/checkout@v6" in workflow
        assert "uses: actions/setup-python@v6" in workflow

    assert "uses: actions/upload-artifact@v7" in daily


def test_gitignore_keeps_local_personal_site_playground_out_of_repo() -> None:
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")

    assert "playgrounds/M-Schuyler.github.io/" in gitignore


def test_workflows_accept_twelvedata_configuration() -> None:
    intraday = read_workflow("intraday-market-scan.yml")
    close = read_workflow("market-close-alert.yml")
    daily = read_workflow("daily-ai-market-brief.yml")

    for workflow in (intraday, close, daily):
        assert 'MARKET_PROVIDER: ${{ vars.MARKET_PROVIDER || \'yahoo\' }}' in workflow
        assert "TWELVEDATA_API_KEY: ${{ secrets.TWELVEDATA_API_KEY }}" in workflow
