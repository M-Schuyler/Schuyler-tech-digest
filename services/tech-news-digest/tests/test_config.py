from __future__ import annotations

from news_digest.config import load_runtime_settings


def test_runtime_settings_do_not_fallback_to_legacy_single_bot_env(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "legacy-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "legacy-chat")
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN_MAIN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID_MAIN", raising=False)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN_SIDE", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID_SIDE", raising=False)

    settings = load_runtime_settings()

    assert not settings.main_bot.enabled
    assert not settings.side_bot.enabled
