from __future__ import annotations

INTERNAL_METADATA_PATTERNS = (
    "focus tags",
    "tier 1 source",
    "tier 2 source",
    "tier 3 source",
    "tier source",
    "mapped symbols",
    "official source",
    "watched entity",
    "source signal",
)


def sanitize_public_section(text: str) -> str:
    lines = []
    for line in (text or "").splitlines():
        if _leaks_internal_metadata(line):
            continue
        if line.strip():
            lines.append(line)
    return "\n".join(lines).strip()


def _leaks_internal_metadata(text: str) -> bool:
    lower = (text or "").lower()
    return any(pattern in lower for pattern in INTERNAL_METADATA_PATTERNS)
