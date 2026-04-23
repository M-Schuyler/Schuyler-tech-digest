from __future__ import annotations

from collections.abc import Sequence

from ..models import CloseSummary, WatchSignal


class CrossCorrelator:
    def compose(
        self,
        *,
        top_three: Sequence[str],
        close_summary: CloseSummary | None,
        watchlist: Sequence[WatchSignal],
    ) -> str:
        lines: list[str] = []

        if close_summary:
            lines.append(close_summary.closing_verdict)
            if close_summary.strongest_assets:
                leaders = " / ".join(close_summary.strongest_assets[:2])
                lines.append(f"昨夜最先响应主线的是 {leaders}，这比泛泛的新闻热度更值得信。")
            if close_summary.weakest_assets:
                laggards = " / ".join(close_summary.weakest_assets[:2])
                lines.append(f"相反，{laggards} 还没跟上，说明资金并不是无差别地追科技。")
        else:
            lines.append("前一交易日还没有现成的收盘结案数据，今天先用新闻主线去定义观察重点。")

        if top_three:
            lines.append(f"把早报的三条判断落到价格里，本质上是在看：{_topic_anchor(top_three[0])}")

        if watchlist:
            lead = watchlist[0]
            lines.append(f"下一交易日优先盯 {lead.symbol}，因为{lead.reason}。")

        bullets = [f"• {item.symbol}：{item.reason}" for item in watchlist[:3]]
        return "\n".join([*lines, *bullets])


def _topic_anchor(topic: str) -> str:
    trimmed = topic.rstrip("。")
    return trimmed if trimmed else "主线有没有继续扩散"
