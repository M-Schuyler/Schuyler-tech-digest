from __future__ import annotations

from collections.abc import Iterable

from ..config import MARKET_SYMBOLS


def ranked_market_symbols() -> tuple[str, ...]:
    return tuple(
        symbol
        for symbol, _ in sorted(
            MARKET_SYMBOLS.items(),
            key=lambda item: -item[1].watchlist_priority,
        )
    )


def pick_symbol_scope(*, budget: int, prioritized: Iterable[str] = ()) -> tuple[str, ...]:
    normalized_budget = max(1, min(budget, len(MARKET_SYMBOLS)))
    ordered: list[str] = []

    def add(symbol: str) -> None:
        normalized = symbol.strip().upper()
        if normalized not in MARKET_SYMBOLS:
            return
        if normalized in ordered:
            return
        if len(ordered) >= normalized_budget:
            return
        ordered.append(normalized)

    for symbol in prioritized:
        add(symbol)
    for symbol in ranked_market_symbols():
        add(symbol)

    return tuple(ordered)
