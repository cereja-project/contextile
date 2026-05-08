from __future__ import annotations


def estimate_tokens(text: str) -> int:
    """Approximate token count using a simple character-based heuristic.

    This keeps the MVP dependency-free. It is intentionally approximate.
    """
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)


def truncate_to_token_budget(text: str, max_tokens: int) -> str:
    if max_tokens <= 0:
        return ""
    max_chars = max_tokens * 4
    if len(text) <= max_chars:
        return text
    return text[: max(0, max_chars - 20)].rstrip() + "\n...[truncated]"
