# --- src/waa/detect.py ---
from pathlib import Path
from typing import Union, Set

EN_QUESTION_STARTS = (
    "what","why","how","when","where","who","which",
    "can","could","should","would","do","does","did",
    "is","are","am","will","may","might"
)

def is_english_question(text: str, lang: str) -> bool:
    if (lang or "").lower() != "en":
        return False
    t = (text or "").strip().lower()
    if not t:
        return False
    return t.endswith("?") or any(t.startswith(p + " ") for p in EN_QUESTION_STARTS)

PathLike = Union[str, Path]

def load_keywords(path: PathLike) -> Set[str]:
    p = Path(path)
    if not p.exists():
        return set()
    return {line.strip().lower() for line in p.read_text(encoding="utf-8").splitlines() if line.strip()}

def contains_keyword(text: str, keywords: Set[str]) -> bool:
    if not keywords:
        return True
    s = (text or "").lower()
    return any(k in s for k in keywords)