"""Unicode-based attacks for tokenizer confusion and hidden payload delivery.

Techniques:
- Homoglyph substitution: visually identical characters from different scripts
- Zero-width character injection: invisible characters that affect tokenization
- Bidirectional text overrides: text reads differently to parser vs renderer
- Combining character stacking: valid Unicode that explodes token counts
"""

from __future__ import annotations

import random
from typing import Sequence

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
ZWJ = "\u200d"       # Zero-width joiner
ZWNJ = "\u200c"      # Zero-width non-joiner
ZWSP = "\u200b"      # Zero-width space
ZW_CHARS = [ZWJ, ZWNJ, ZWSP]

# Bidirectional overrides
RLO = "\u202e"        # Right-to-left override
LRO = "\u202d"        # Left-to-right override
PDF = "\u202c"        # Pop directional formatting
RLI = "\u2067"        # Right-to-left isolate
LRI = "\u2066"        # Left-to-right isolate
PDI = "\u2069"        # Pop directional isolate

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
    """Replace a fraction of substitutable characters with visually identical homoglyphs.

    Args:
        text: Input text
        rate: Fraction of eligible characters to replace (0.0-1.0)
        rng: Optional seeded Random for deterministic output
    """
    r = rng or random.Random()
    chars = []
    for ch in text:
        if ch in HOMOGLYPH_MAP and r.random() < rate:
            chars.append(r.choice(HOMOGLYPH_MAP[ch]))
        else:
            chars.append(ch)
    return "".join(chars)


def inject_zero_width(text: str, density: int = 2, rng: random.Random | None = None) -> str:
    """Insert zero-width characters between visible characters.

    Args:
        text: Input text
        density: Average number of ZW chars to insert between each visible char
        rng: Optional seeded Random for deterministic output
    """
    r = rng or random.Random()
    chars = []
    for ch in text:
        chars.append(ch)
        if ch.strip():  # Don't inject around whitespace
            for _ in range(r.randint(1, density)):
                chars.append(r.choice(ZW_CHARS))
    return "".join(chars)


def encode_hidden_payload(visible_text: str, hidden_payload: str) -> str:
    """Embed a hidden text payload using zero-width characters within visible text.

    The hidden payload is encoded as a sequence of ZWJ (1) and ZWNJ (0) characters,
    representing each byte of the payload in binary. These are interspersed between
    visible characters.
    """
    # Encode payload to binary ZW sequence
    zw_encoded = []
    for byte in hidden_payload.encode("utf-8"):
        for bit in format(byte, "08b"):
            zw_encoded.append(ZWJ if bit == "1" else ZWNJ)
        zw_encoded.append(ZWSP)  # Byte separator

    # Intersperse among visible characters
    result = []
    zw_idx = 0
    for ch in visible_text:
        result.append(ch)
        # Insert some ZW chars after each visible char
        chars_to_insert = min(3, len(zw_encoded) - zw_idx)
        for _ in range(chars_to_insert):
            if zw_idx < len(zw_encoded):
                result.append(zw_encoded[zw_idx])
                zw_idx += 1

    # Append remaining ZW chars at the end
    while zw_idx < len(zw_encoded):
        result.append(zw_encoded[zw_idx])
        zw_idx += 1

    return "".join(result)


def apply_bidi_attack(visible_text: str, hidden_text: str) -> str:
    """Create text that reads differently to a parser vs a visual renderer.

    The visible_text is what humans see. The hidden_text is what a parser
    processing raw characters encounters.
    """
    # RLO makes everything after it render right-to-left
    # We embed hidden text in an RTL override context
    return f"{visible_text}{RLI}{hidden_text}{PDI}"


def zalgoify(text: str, intensity: int = 5, rng: random.Random | None = None) -> str:
    """Stack combining diacritical marks on characters to create Zalgo text.

    Valid Unicode but massively inflates token counts and creates visual chaos.

    Args:
        text: Input text
        intensity: Max number of combining marks per character
        rng: Optional seeded Random for deterministic output
    """
    r = rng or random.Random()
    result = []
    for ch in text:
        result.append(ch)
        if ch.strip():  # Only stack on visible chars
            n_marks = r.randint(1, intensity)
            for _ in range(n_marks):
                result.append(r.choice(COMBINING_MARKS))
    return "".join(result)


def strategic_homoglyphs(text: str, seed: int | None = None) -> str:
    """Apply homoglyphs strategically to maximize tokenizer damage.

    Instead of random substitution, this targets:
    1. High-frequency English words (the, is, of, and, etc.) — pollutes the most common tokens
    2. Technical keywords — corrupts domain-specific embeddings
    3. Named entities — creates ghost entities in knowledge graphs
    4. Sentence-initial words — affects chunking and boundary detection

    The substitution rate varies by word importance to avoid uniform patterns
    that could be detected by a simple character-set consistency check.
    """
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
            # High-frequency words: substitute at 60% rate
            result_words.append(apply_homoglyphs(word, rate=0.6, rng=rng))
        elif word_lower in TECH_TARGETS:
            # Technical terms: substitute at 40% rate
            result_words.append(apply_homoglyphs(word, rate=0.4, rng=rng))
        elif i == 0 or (i > 0 and words[i - 1].endswith(".")):
            # Sentence-initial words: substitute at 30% rate
            result_words.append(apply_homoglyphs(word, rate=0.3, rng=rng))
        elif len(word) > 6 and rng.random() < 0.15:
            # Longer words: occasional substitution
            result_words.append(apply_homoglyphs(word, rate=0.2, rng=rng))
        else:
            result_words.append(word)

    return " ".join(result_words)


# ── Normalization-aware confusables ────────────────────────────────────
# Characters that look identical but behave differently under Unicode normalization.
# NFC normalizes combining sequences; NFKC also folds compatibility equivalents.
# Pipelines that normalize to NFKC will map these to ASCII, but ones using NFC won't.
# This creates SPLIT TOKENS — the same visual text maps to different token IDs
# depending on which normalization the pipeline applies.
NORMALIZATION_CONFUSABLES: dict[str, list[tuple[str, str]]] = {
    # char → [(replacement, survives_which_normalization), ...]
    # "nfc_only" = survives NFC but NFKC maps it to ASCII (creates split)
    # "both" = survives both NFC and NFKC (like Cyrillic homoglyphs)
    "a": [("\uff41", "nfc_only")],     # Fullwidth ａ → NFKC maps to 'a'
    "b": [("\uff42", "nfc_only")],     # Fullwidth ｂ
    "c": [("\uff43", "nfc_only")],     # Fullwidth ｃ
    "d": [("\uff44", "nfc_only")],     # Fullwidth ｄ
    "e": [("\uff45", "nfc_only")],     # Fullwidth ｅ
    "f": [("\uff46", "nfc_only")],     # Fullwidth ｆ
    "i": [("\u2170", "nfc_only")],     # Small Roman numeral ⅰ
    "v": [("\u2174", "nfc_only")],     # Small Roman numeral ⅴ
    "x": [("\u2179", "nfc_only")],     # Small Roman numeral ⅹ
    "1": [("\u2460", "nfc_only")],     # Circled digit ①  (visual '1')
    "2": [("\u2461", "nfc_only")],     # Circled digit ②
    "3": [("\u2462", "nfc_only")],     # Circled digit ③
    "-": [("\u2010", "both"), ("\u2011", "both"), ("\u2012", "both")],  # Various hyphens
    " ": [("\u00a0", "both"), ("\u2000", "nfc_only"), ("\u2003", "nfc_only")],  # NBSP, en quad, em space
    ".": [("\u2024", "nfc_only")],     # One dot leader ․
    ",": [("\u201a", "nfc_only")],     # Single low-9 quotation mark ‚ (looks like comma)
}


def apply_normalization_confusables(
    text: str,
    rate: float = 0.15,
    mode: str = "mixed",
    rng: random.Random | None = None,
) -> str:
    """Replace characters with normalization-sensitive confusables.

    Args:
        text: Input text
        rate: Fraction of eligible characters to replace
        mode: "nfc_only" (max split), "both" (survives all normalization), "mixed"
        rng: Optional seeded Random
    """
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
    """Apply multiple Unicode attacks in combination.

    Args:
        text: Base visible text
        homoglyph_rate: Rate of homoglyph substitution (ignored if strategic=True)
        zwc_density: Zero-width character injection density (0 to disable)
        zalgo_intensity: Zalgo combining mark intensity (0 to disable)
        hidden_payload: Optional hidden payload to encode in ZW chars
        seed: Random seed for deterministic output
        strategic: Use strategic targeting instead of random rate
        normalization_confusable_rate: Rate of normalization-sensitive replacements
    """
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
