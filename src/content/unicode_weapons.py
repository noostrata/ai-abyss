# AI Abyss — Proof of Concept (2026)
# https://github.com/terrorswift/ai-abyss
# Unicode-based attacks — homoglyphs, zero-width injection, and Zalgo text.
from __future__ import annotations

import random

# ── Homoglyph mappings ─────────────────────────────────────────────
# Latin → visually identical Cyrillic/Greek equivalents
HOMOGLYPH_MAP: dict[str, list[str]] = {
    "a": ["\u0430"],          # Cyrillic а
    "c": ["\u0441"],          # Cyrillic с
    "d": ["\u0501"],          # Cyrillic ԁ
    "e": ["\u0435"],          # Cyrillic е
    "h": ["\u04bb"],          # Cyrillic һ
    "i": ["\u0456"],          # Cyrillic і
    "j": ["\u0458"],          # Cyrillic ј
    "k": ["\u043a"],          # Cyrillic к
    "l": ["\u04cf"],          # Cyrillic ӏ
    "o": ["\u043e"],          # Cyrillic о
    "p": ["\u0440"],          # Cyrillic р
    "q": ["\u051b"],          # Cyrillic ԛ
    "s": ["\u0455"],          # Cyrillic ѕ
    "w": ["\u051d"],          # Cyrillic ԝ
    "x": ["\u0445"],          # Cyrillic х
    "y": ["\u0443"],          # Cyrillic у
    "A": ["\u0410"],          # Cyrillic А
    "B": ["\u0412"],          # Cyrillic В
    "C": ["\u0421"],          # Cyrillic С
    "E": ["\u0415"],          # Cyrillic Е
    "H": ["\u041d"],          # Cyrillic Н
    "K": ["\u041a"],          # Cyrillic К
    "M": ["\u041c"],          # Cyrillic М
    "N": ["\u039d"],          # Greek Ν
    "O": ["\u041e"],          # Cyrillic О
    "P": ["\u0420"],          # Cyrillic Р
    "S": ["\u0405"],          # Cyrillic Ѕ
    "T": ["\u0422"],          # Cyrillic Т
    "X": ["\u0425"],          # Cyrillic Х
    "Y": ["\u04ae"],          # Cyrillic Ү
    "Z": ["\u0396"],          # Greek Ζ
}

# Zero-width characters
ZWJ = "\u200d"
ZWNJ = "\u200c"
ZWSP = "\u200b"
ZW_CHARS = [ZWJ, ZWNJ, ZWSP]

# Combining diacritical marks (for Zalgo text)
COMBINING_MARKS = [
    "\u0300", "\u0301", "\u0302", "\u0303", "\u0304", "\u0305", "\u0306", "\u0307",
    "\u0308", "\u0309", "\u030a", "\u030b", "\u030c", "\u030d", "\u030e", "\u030f",
    "\u0310", "\u0311", "\u0312", "\u0313", "\u0314", "\u0315", "\u0316", "\u0317",
    "\u0318", "\u0319", "\u031a", "\u031b", "\u031c", "\u031d", "\u031e", "\u031f",
    "\u0320", "\u0321", "\u0322", "\u0323", "\u0324", "\u0325", "\u0326", "\u0327",
    "\u0328", "\u0329", "\u032a", "\u032b", "\u032c", "\u032d", "\u032e", "\u032f",
    "\u0330", "\u0331", "\u0332", "\u0333", "\u0334", "\u0335", "\u0336", "\u0337",
    "\u0338", "\u0339", "\u033a", "\u033b", "\u033c", "\u033d", "\u033e", "\u033f",
]


def apply_homoglyphs(text: str, rate: float = 0.3, rng: random.Random | None = None) -> str:
    r = rng or random.Random()
    chars = []
    for ch in text:
        if ch in HOMOGLYPH_MAP and r.random() < rate:
            chars.append(r.choice(HOMOGLYPH_MAP[ch]))
        else:
            chars.append(ch)
    return "".join(chars)


def inject_zero_width(text: str, density: int = 2, rng: random.Random | None = None) -> str:
    r = rng or random.Random()
    chars = []
    for ch in text:
        chars.append(ch)
        if ch.strip():
            for _ in range(r.randint(1, density)):
                chars.append(r.choice(ZW_CHARS))
    return "".join(chars)


def encode_hidden_payload(visible_text: str, hidden_payload: str) -> str:
    # Encode payload to binary ZW sequence
    zw_encoded = []
    for byte in hidden_payload.encode("utf-8"):
        for bit in format(byte, "08b"):
            zw_encoded.append(ZWJ if bit == "1" else ZWNJ)
        zw_encoded.append(ZWSP)

    # Intersperse among visible characters
    result = []
    zw_idx = 0
    for ch in visible_text:
        result.append(ch)
        chars_to_insert = min(3, len(zw_encoded) - zw_idx)
        for _ in range(chars_to_insert):
            if zw_idx < len(zw_encoded):
                result.append(zw_encoded[zw_idx])
                zw_idx += 1

    while zw_idx < len(zw_encoded):
        result.append(zw_encoded[zw_idx])
        zw_idx += 1

    return "".join(result)


def zalgoify(text: str, intensity: int = 5, rng: random.Random | None = None) -> str:
    r = rng or random.Random()
    result = []
    for ch in text:
        result.append(ch)
        if ch.strip():
            n_marks = r.randint(1, intensity)
            for _ in range(n_marks):
                result.append(r.choice(COMBINING_MARKS))
    return "".join(result)


def strategic_homoglyphs(text: str, seed: int | None = None) -> str:
    rng = random.Random(seed) if seed is not None else random.Random()

    # High-frequency words get high substitution rate (most training impact)
    HIGH_FREQ_TARGETS = {
        "the", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would",
        "could", "should", "may", "might", "can", "shall",
        "this", "that", "these", "those", "which", "who", "what",
        "not", "no", "nor", "but", "and", "or", "so", "if", "then",
        "also", "very", "often", "however", "therefore", "thus",
        "from", "with", "for", "about", "into", "through", "between",
    }
    # Technical terms — corrupting these damages domain-specific embeddings
    TECH_TARGETS = {
        "algorithm", "model", "data", "system", "network", "server",
        "protocol", "security", "encryption", "authentication",
        "performance", "architecture", "deployment", "configuration",
        "database", "interface", "framework", "pipeline", "process",
        "analysis", "research", "method", "approach", "implementation",
        "function", "parameter", "variable", "endpoint", "response",
    }

    words = text.split()
    result_words = []

    for i, word in enumerate(words):
        word_lower = word.lower().strip(".,;:!?\"'()[]{}—–-")

        if word_lower in HIGH_FREQ_TARGETS:
            result_words.append(apply_homoglyphs(word, rate=0.6, rng=rng))
        elif word_lower in TECH_TARGETS:
            result_words.append(apply_homoglyphs(word, rate=0.4, rng=rng))
        elif i == 0 or (i > 0 and words[i - 1].endswith(".")):
            result_words.append(apply_homoglyphs(word, rate=0.3, rng=rng))
        elif len(word) > 6 and rng.random() < 0.15:
            result_words.append(apply_homoglyphs(word, rate=0.2, rng=rng))
        else:
            result_words.append(word)

    return " ".join(result_words)


# ── Normalization-aware confusables ────────────────────────────────────
# Characters that look identical but behave differently under Unicode normalization.
# NFC normalizes combining sequences; NFKC also folds compatibility equivalents.
# This creates SPLIT TOKENS — the same visual text maps to different token IDs
# depending on which normalization the pipeline applies.
NORMALIZATION_CONFUSABLES: dict[str, list[tuple[str, str]]] = {
    "a": [("\uff41", "nfc_only")],
    "b": [("\uff42", "nfc_only")],
    "c": [("\uff43", "nfc_only")],
    "d": [("\uff44", "nfc_only")],
    "e": [("\uff45", "nfc_only")],
    "f": [("\uff46", "nfc_only")],
    "i": [("\u2170", "nfc_only")],
    "v": [("\u2174", "nfc_only")],
    "x": [("\u2179", "nfc_only")],
    "1": [("\u2460", "nfc_only")],
    "2": [("\u2461", "nfc_only")],
    "3": [("\u2462", "nfc_only")],
    "-": [("\u2010", "both"), ("\u2011", "both"), ("\u2012", "both")],
    " ": [("\u00a0", "both"), ("\u2000", "nfc_only"), ("\u2003", "nfc_only")],
    ".": [("\u2024", "nfc_only")],
    ",": [("\u201a", "nfc_only")],
}


def apply_normalization_confusables(
    text: str,
    rate: float = 0.15,
    mode: str = "mixed",
    rng: random.Random | None = None,
) -> str:
    r = rng or random.Random()
    chars = []
    for ch in text:
        if ch in NORMALIZATION_CONFUSABLES and r.random() < rate:
            candidates = NORMALIZATION_CONFUSABLES[ch]
            if mode == "mixed":
                replacement, _ = r.choice(candidates)
            else:
                filtered = [(rep, m) for rep, m in candidates if m == mode or mode == "mixed"]
                if filtered:
                    replacement, _ = r.choice(filtered)
                else:
                    replacement = ch
            chars.append(replacement)
        else:
            chars.append(ch)
    return "".join(chars)


def mixed_attack(
    text: str,
    homoglyph_rate: float = 0.2,
    zwc_density: int = 1,
    zalgo_intensity: int = 0,
    hidden_payload: str | None = None,
    seed: int | None = None,
    strategic: bool = False,
    normalization_confusable_rate: float = 0.0,
) -> str:
    rng = random.Random(seed) if seed is not None else random.Random()

    result = text
    if strategic:
        result = strategic_homoglyphs(result, seed=seed)
    elif homoglyph_rate > 0:
        result = apply_homoglyphs(result, rate=homoglyph_rate, rng=rng)
    if normalization_confusable_rate > 0:
        result = apply_normalization_confusables(result, rate=normalization_confusable_rate, rng=rng)
    if hidden_payload:
        result = encode_hidden_payload(result, hidden_payload)
    elif zwc_density > 0:
        result = inject_zero_width(result, density=zwc_density, rng=rng)
    if zalgo_intensity > 0:
        result = zalgoify(result, intensity=zalgo_intensity, rng=rng)

    return result
