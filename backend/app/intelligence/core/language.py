"""Lightweight language detection for Document Intelligence.

Heuristic-based detector for the scripts and languages Nexora tenants commonly
process (Uzbek, Russian, English). It is intentionally dependency-free and used
only to tag documents with a language hint.
"""

import re

LATIN_CYRILLIC_SAMPLE = 500


def detect_language(text: str) -> str:
    """Returns a two-letter language code based on dominant script and markers."""
    sample = text[:LATIN_CYRILLIC_SAMPLE] or ""

    cyrillic_chars = len(re.findall(r"[А-Яа-яЁё]", sample))
    latin_chars = len(re.findall(r"[A-Za-z]", sample))

    if cyrillic_chars == 0 and latin_chars == 0:
        # CJK / arabic / other script quick hints
        if re.search(r"[\u4e00-\u9fff]", sample):
            return "zh"
        if re.search(r"[\u0600-\u06ff]", sample):
            return "ar"
        return "und"

    if cyrillic_chars > latin_chars:
        return _detect_cyrillic_language(sample)

    return _detect_latin_language(sample)


def _detect_cyrillic_language(text: str) -> str:
    # 'ў' and 'қ'/'ғ'/'ҳ' are strong Uzbek-Cyrillic markers
    if re.search(r"[ўқғҳЎҚҒҲ]", text):
        return "uz"
    # 'ы', 'э', 'щ' appear frequently in Russian
    if re.search(r"[ыэщЫЭЩ]", text):
        return "ru"
    return "ru"


def _detect_latin_language(text: str) -> str:
    # Uzbek Latin-specific letters: o', g', sh/ch combinations are common too,
    # but the apostrophe digraphs are the strongest signal.
    if re.search(r"[oO]'|[gG]'|[oO]ʻ|[gG]ʻ", text):
        return "uz"

    stopword_score = {
        "uz": sum(text.lower().count(w) for w in ("va ", "bu ", "uchun", "bilan", "ham", "biz", "siz", "emas", "emasdir")),
        "en": sum(text.lower().count(w) for w in ("the ", "and ", "with", "for ", "this", "that", "are ", "is ")),
        "ru": sum(text.lower().count(w) for w in ("и ", "для", "что", "это", "с ", "на ", "в ", "не ")),
    }
    best = max(stopword_score, key=stopword_score.get)
    return best if stopword_score[best] > 0 else "en"


def detect_language_short(text: str) -> str:
    """Alias returning a shorter normalized code used by the document model."""
    return detect_language(text)
