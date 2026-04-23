from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import time
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
REPORT_DIR = BASE_DIR / "reports"
STATE_DB_PATH = DATA_DIR / "state.db"
ASSET_DIR = REPORT_DIR / "assets"


@dataclass(frozen=True)
class Settings:
    rss_sources: dict[str, str]
    max_articles_per_source: int = 20
    request_timeout: int = 20
    openai_model: str = "gpt-4o-mini"
    gemini_model: str = "gemini-2.5-flash"
    max_briefing_items: int = 10


@dataclass(frozen=True)
class BotConfig:
    token: str
    chat_id: str

    @property
    def enabled(self) -> bool:
        return bool(self.token and self.chat_id)


@dataclass(frozen=True)
class SymbolProfile:
    symbol: str
    yahoo_symbol: str
    bucket: str
    label: str
    watchlist_priority: int


@dataclass(frozen=True)
class RuntimeSettings:
    market_provider: str
    twelvedata_api_key: str
    market_symbol_budget: int
    state_db_url: str
    state_db_auth_token: str
    state_db_local_path: Path
    main_bot: BotConfig
    side_bot: BotConfig
    brief_timezone: str
    market_timezone: str
    brief_send_time_sh: time
    brief_cutoff_time_sh: time
    close_alert_time_ny: time
    intraday_start_ny: time
    intraday_end_ny: time
    intraday_interval_minutes: int
    volume_baseline_lookback_days: int
    volume_baseline_multiplier: float
    max_intraday_alerts_per_day: int
    chart_default_symbols: tuple[str, ...]
    font_path: str
    chart_font_path: str
    min_official_source_weight: int


MARKET_SYMBOLS: dict[str, SymbolProfile] = {
    "QQQ": SymbolProfile("QQQ", "QQQ", "index", "Nasdaq 100", 10),
    "SPY": SymbolProfile("SPY", "SPY", "index", "S&P 500", 9),
    "NVDA": SymbolProfile("NVDA", "NVDA", "tech_stock", "NVIDIA", 10),
    "AMD": SymbolProfile("AMD", "AMD", "tech_stock", "AMD", 8),
    "TSLA": SymbolProfile("TSLA", "TSLA", "tech_stock", "Tesla", 7),
    "META": SymbolProfile("META", "META", "tech_stock", "Meta", 7),
    "MSFT": SymbolProfile("MSFT", "MSFT", "tech_stock", "Microsoft", 9),
    "GOOGL": SymbolProfile("GOOGL", "GOOGL", "tech_stock", "Google", 8),
    "AAPL": SymbolProfile("AAPL", "AAPL", "tech_stock", "Apple", 8),
    "BTC": SymbolProfile("BTC", "BTC-USD", "crypto", "Bitcoin", 10),
    "ETH": SymbolProfile("ETH", "ETH-USD", "crypto", "Ethereum", 8),
}
INDEX_SYMBOLS = tuple(symbol for symbol, profile in MARKET_SYMBOLS.items() if profile.bucket == "index")
TECH_STOCK_SYMBOLS = tuple(symbol for symbol, profile in MARKET_SYMBOLS.items() if profile.bucket == "tech_stock")
CRYPTO_SYMBOLS = tuple(symbol for symbol, profile in MARKET_SYMBOLS.items() if profile.bucket == "crypto")


DEFAULT_SETTINGS = Settings(
    rss_sources={
        "TechCrunch": "https://techcrunch.com/feed/",
        "The Verge": "https://www.theverge.com/rss/index.xml",
        "Wired": "https://www.wired.com/feed/rss",
        "MIT Technology Review": "https://www.technologyreview.com/feed/",
        "Ars Technica": "http://feeds.arstechnica.com/arstechnica/index",
    },
    max_articles_per_source=int(os.getenv("MAX_ARTICLES_PER_SOURCE", "20")),
    request_timeout=int(os.getenv("REQUEST_TIMEOUT", "20")),
    openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
    max_briefing_items=int(os.getenv("MAX_BRIEFING_ITEMS", "10")),
)


def load_runtime_settings() -> RuntimeSettings:
    main_token = os.getenv("TELEGRAM_BOT_TOKEN_MAIN", "").strip()
    main_chat = os.getenv("TELEGRAM_CHAT_ID_MAIN", "").strip()
    side_token = os.getenv("TELEGRAM_BOT_TOKEN_SIDE", "").strip()
    side_chat = os.getenv("TELEGRAM_CHAT_ID_SIDE", "").strip()
    main_bot = BotConfig(token=main_token, chat_id=main_chat)
    side_bot = BotConfig(token=side_token, chat_id=side_chat)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)

    return RuntimeSettings(
        market_provider=os.getenv("MARKET_PROVIDER", "yahoo").strip().lower() or "yahoo",
        twelvedata_api_key=os.getenv("TWELVEDATA_API_KEY", "").strip(),
        market_symbol_budget=_resolve_market_symbol_budget(
            provider=os.getenv("MARKET_PROVIDER", "yahoo").strip().lower() or "yahoo",
            raw_budget=os.getenv("MARKET_SYMBOL_BUDGET", "").strip(),
        ),
        state_db_url=os.getenv("STATE_DB_URL", "").strip(),
        state_db_auth_token=os.getenv("STATE_DB_AUTH_TOKEN", "").strip(),
        state_db_local_path=Path(os.getenv("STATE_DB_LOCAL_PATH", str(STATE_DB_PATH))),
        main_bot=main_bot,
        side_bot=side_bot,
        brief_timezone=os.getenv("BRIEF_TIMEZONE", "Asia/Shanghai"),
        market_timezone=os.getenv("MARKET_TIMEZONE", "America/New_York"),
        brief_send_time_sh=time.fromisoformat(os.getenv("BRIEF_SEND_TIME_SH", "08:00")),
        brief_cutoff_time_sh=time.fromisoformat(os.getenv("BRIEF_CUTOFF_TIME_SH", "07:30")),
        close_alert_time_ny=time.fromisoformat(os.getenv("CLOSE_ALERT_TIME_NY", "16:30")),
        intraday_start_ny=time.fromisoformat(os.getenv("INTRADAY_START_NY", "09:30")),
        intraday_end_ny=time.fromisoformat(os.getenv("INTRADAY_END_NY", "16:00")),
        intraday_interval_minutes=int(os.getenv("INTRADAY_INTERVAL_MINUTES", "15")),
        volume_baseline_lookback_days=int(os.getenv("VOLUME_BASELINE_LOOKBACK_DAYS", "20")),
        volume_baseline_multiplier=float(os.getenv("VOLUME_BASELINE_MULTIPLIER", "1.8")),
        max_intraday_alerts_per_day=int(os.getenv("MAX_INTRADAY_ALERTS_PER_DAY", "5")),
        chart_default_symbols=tuple(
            symbol.strip().upper()
            for symbol in os.getenv("CHART_DEFAULT_SYMBOLS", "QQQ,NVDA,BTC").split(",")
            if symbol.strip()
        ),
        font_path=os.getenv("CARD_FONT_PATH", "").strip(),
        chart_font_path=os.getenv("CHART_FONT_PATH", "").strip(),
        min_official_source_weight=int(os.getenv("MIN_OFFICIAL_SOURCE_WEIGHT", "25")),
    )


def get_symbol_profile(symbol: str) -> SymbolProfile:
    normalized = symbol.strip().upper()
    if normalized not in MARKET_SYMBOLS:
        raise KeyError(f"Unsupported symbol: {symbol}")
    return MARKET_SYMBOLS[normalized]


def _resolve_market_symbol_budget(*, provider: str, raw_budget: str) -> int:
    if raw_budget:
        return max(1, min(int(raw_budget), len(MARKET_SYMBOLS)))
    if provider == "twelvedata":
        return min(8, len(MARKET_SYMBOLS))
    return len(MARKET_SYMBOLS)
