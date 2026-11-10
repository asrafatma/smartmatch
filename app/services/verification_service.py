"""Deterministic, server-side comparison of a claimant's answer with the finder's private clue."""
import re

# Words that carry no identifying information
STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "on", "in", "at", "to", "with", "is", "it", "its", "it's",
    "my", "has", "have", "there", "this", "that", "inside", "for", "from", "by", "as", "are", "was",
    "be", "i", "me", "small", "little", "some", "one", "near", "under", "behind", "front", "back",
}


def _tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    out = set()
    for w in words:
        if w in STOPWORDS or len(w) < 2:
            continue
        # Light, fixed stemming so "stickers" == "sticker", "scratched" ~ "scratch"
        for suffix in ("ing", "ed", "es", "s"):
            if len(w) > 4 and w.endswith(suffix):
                w = w[: -len(suffix)]
                break
        out.add(w)
    return out


def answer_matches_clue(answer: str, clue: str, threshold: float = 0.6) -> bool:
    """True when at least `threshold` of the clue's significant keywords appear in the answer."""
    clue_tokens = _tokens(clue)
    if not clue_tokens:
        return False
    answer_tokens = _tokens(answer)
    overlap = len(clue_tokens & answer_tokens)
    return overlap / len(clue_tokens) >= threshold
