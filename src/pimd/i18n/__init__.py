"""Internationalisation (i18n) support for PiMD.

Provides language-aware typography, RTL detection and handling,
CJK (Chinese, Japanese, Korean) support, and Unicode text processing
for all output formats.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ScriptType(Enum):
    """Text direction and script classification."""
    LTR = "ltr"
    RTL = "rtl"
    CJK = "cjk"
    NEUTRAL = "neutral"


# Unicode ranges for script detection
_RTL_RANGES = [
    (0x0590, 0x05FF),   # Hebrew
    (0x0600, 0x06FF),   # Arabic
    (0x0700, 0x074F),   # Syriac
    (0x0750, 0x077F),   # Arabic Supplement
    (0x08A0, 0x08FF),   # Arabic Extended-A
    (0xFB1D, 0xFB4F),   # Hebrew Presentation Forms
    (0xFB50, 0xFDFF),   # Arabic Presentation Forms-A
    (0xFE70, 0xFEFF),   # Arabic Presentation Forms-B
    (0x1EE00, 0x1EEFF), # Arabic Mathematical
]

_CJK_RANGES = [
    (0x4E00, 0x9FFF),    # CJK Unified Ideographs
    (0x3400, 0x4DBF),    # CJK Unified Ideographs Extension A
    (0x2E80, 0x2EFF),    # CJK Radicals Supplement
    (0x3000, 0x303F),    # CJK Symbols and Punctuation
    (0x3040, 0x309F),    # Hiragana
    (0x30A0, 0x30FF),    # Katakana
    (0xFF00, 0xFFEF),    # Halfwidth and Fullwidth Forms
    (0xAC00, 0xD7AF),    # Hangul Syllables
    (0x1100, 0x11FF),    # Hangul Jamo
    (0x3130, 0x318F),    # Hangul Compatibility Jamo
    (0x31F0, 0x31FF),    # Katakana Phonetic Extensions
    (0x1F200, 0x1F2FF),  # Enclosed Ideographic Supplement
]


def detect_script(text: str) -> ScriptType:
    """Detect the dominant script type in a text string.

    Args:
        text: The text to analyse.

    Returns:
        ScriptType.LTR, ScriptType.RTL, ScriptType.CJK, or ScriptType.NEUTRAL.
    """
    if not text:
        return ScriptType.NEUTRAL

    rtl_score = 0
    cjk_score = 0
    total_char = 0

    for ch in text:
        cp = ord(ch)
        if cp < 0x20:
            continue
        total_char += 1

        for start, end in _RTL_RANGES:
            if start <= cp <= end:
                rtl_score += 1
                break

        for start, end in _CJK_RANGES:
            if start <= cp <= end:
                cjk_score += 1
                break

    if total_char == 0:
        return ScriptType.NEUTRAL

    if rtl_score > 0:
        return ScriptType.RTL
    if cjk_score > 0:
        return ScriptType.CJK
    return ScriptType.LTR


_RTL_LANGUAGES = frozenset({
    "ar", "arc", "dv", "fa", "ha", "he", "khw", "ks", "ku", "ps",
    "ur", "yi", "ckb", "prs", "sd", "ug",
})

_CJK_LANGUAGES = frozenset({
    "zh", "ja", "ko", "vi",
})


def is_rtl_language(language: str) -> bool:
    """Check if a language code is a right-to-left language.

    Args:
        language: ISO 639 language code.

    Returns:
        True if the language is RTL.
    """
    lang = language.split("-")[0].lower()
    return lang in _RTL_LANGUAGES


def is_cjk_language(language: str) -> bool:
    """Check if a language code is a CJK language.

    Args:
        language: ISO 639 language code.

    Returns:
        True if the language is CJK.
    """
    lang = language.split("-")[0].lower()
    return lang in _CJK_LANGUAGES


@dataclass
class LanguageConfig:
    """Language-specific typography configuration.

    Attributes:
        language: ISO 639 language code (e.g., 'en', 'ar', 'zh').
        script: Detected script type.
        font_family: Recommended font family for this language.
        font_size: Base font size in points.
        line_height: Line height multiplier.
        paragraph_spacing: Space between paragraphs in ems.
        digit_font: Font for digits (None = use body font).
        use_verb: Use verb form instead of "is/are" for metadata.
    """
    language: str = "en"
    script: ScriptType = ScriptType.LTR
    font_family: str = "serif"
    font_size: float = 11.0
    line_height: float = 1.6
    paragraph_spacing: float = 0.8
    digit_font: str | None = None
    use_verb: bool = False


# Language-specific configuration presets
LANGUAGE_CONFIGS: dict[str, LanguageConfig] = {
    "en": LanguageConfig("en", ScriptType.LTR, "Georgia, 'Times New Roman', serif", 11),
    "ar": LanguageConfig("ar", ScriptType.RTL, "Amiri, 'Scheherazade New', serif", 12, 1.8, 1.0),
    "fa": LanguageConfig("fa", ScriptType.RTL, "Vazirmatn, 'Noto Naskh Arabic', serif", 12, 1.8, 1.0),
    "ur": LanguageConfig("ur", ScriptType.RTL, "Jameel Noori Nastaleeq, 'Noto Nastaliq Urdu', serif", 13, 2.0, 1.0),
    "he": LanguageConfig("he", ScriptType.RTL, "Miriam Libre, 'Noto Sans Hebrew', sans-serif", 11, 1.6, 0.8),
    "zh": LanguageConfig("zh", ScriptType.CJK, "'Noto Serif CJK SC', 'Source Han Serif SC', serif", 11, 1.8, 0.5),
    "zh-CN": LanguageConfig("zh-CN", ScriptType.CJK, "'Noto Serif CJK SC', 'Source Han Serif SC', serif", 11, 1.8, 0.5),
    "zh-TW": LanguageConfig("zh-TW", ScriptType.CJK, "'Noto Serif CJK TC', 'Source Han Serif TC', serif", 11, 1.8, 0.5),
    "ja": LanguageConfig("ja", ScriptType.CJK, "'Noto Serif CJK JP', 'Source Han Serif', serif", 11, 1.8, 0.5),
    "ko": LanguageConfig("ko", ScriptType.CJK, "'Noto Serif CJK KR', 'Source Han Serif K', serif", 11, 1.8, 0.5),
}


def get_language_config(language: str) -> LanguageConfig:
    """Get the typography configuration for a language.

    Args:
        language: ISO 639 language code.

    Returns:
        LanguageConfig for the given language, or a default LTR config.
    """
    if language in LANGUAGE_CONFIGS:
        return LANGUAGE_CONFIGS[language]
    lang_base = language.split("-")[0]
    if lang_base in LANGUAGE_CONFIGS:
        return LANGUAGE_CONFIGS[lang_base]

    if is_rtl_language(language):
        return LanguageConfig(language, ScriptType.RTL, "serif", 12, 1.8, 1.0)
    if is_cjk_language(language):
        return LanguageConfig(language, ScriptType.CJK, "serif", 11, 1.8, 0.5)

    return LANGUAGE_CONFIGS["en"]


def reshape_arabic(text: str) -> str:
    """Reshape Arabic text for proper rendering.

    Uses arabic_reshaper if available; falls back to the original text.

    Args:
        text: Arabic text string.

    Returns:
        Reshaped text suitable for rendering.
    """
    try:
        import arabic_reshaper
        return arabic_reshaper.reshape(text)
    except ImportError:
        return text


def apply_bidi(text: str, base_dir: str = "auto") -> str:
    """Apply bidirectional Unicode algorithm to text.

    Uses the `bidi` package if available; falls back to the original text.

    Args:
        text: Text with mixed LTR/RTL content.
        base_dir: Base direction ('ltr', 'rtl', or 'auto').

    Returns:
        Reordered text suitable for display.
    """
    try:
        from bidi.algorithm import get_display
        if base_dir == "auto":
            script = detect_script(text)
            base_dir = "rtl" if script == ScriptType.RTL else "ltr"
        # python-bidi expects single-char: 'L' (LTR), 'R' (RTL), or 'AL' (Arabic letter)
        mapped = {"ltr": "L", "rtl": "R", "auto": "L"}
        return get_display(text, base_dir=mapped.get(base_dir.lower(), "L"))
    except ImportError:
        return text


def process_text_for_language(text: str, language: str = "en") -> str:
    """Process text according to language rules.

    Handles Arabic reshaping, bidirectional reordering, and any
    other language-specific transformations.

    Args:
        text: The text to process.
        language: ISO 639 language code.

    Returns:
        Processed text.
    """
    if is_rtl_language(language):
        text = reshape_arabic(text)
        text = apply_bidi(text, base_dir="rtl")
    return text


# ── DOCX-level i18n helpers ──────────────────────────────────────

def configure_docx_for_language(document: Any, language: str = "en") -> None:
    """Configure a python-docx Document for language-specific rendering.

    Sets the document language, RTL direction, and font preferences.

    Args:
        document: A python-docx Document object.
        language: ISO 639 language code.
    """
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    lang_config = get_language_config(language)
    is_rtl = lang_config.script == ScriptType.RTL

    if is_rtl:
        for section in document.sections:
            sect_pr = section._sectPr
            if sect_pr is None:
                sect_pr = OxmlElement("w:sectPr")
                section._sectPr = sect_pr
            # Set bidi for the section
            bidi = sect_pr.find(qn("w:bidi"))
            if bidi is None:
                bidi = OxmlElement("w:bidi")
                sect_pr.append(bidi)

    # Set document-level language
    body = document.element.body
    for p in body.iterchildren(qn("w:p")):
        p_pr = p.find(qn("w:pPr"))
        if p_pr is None:
            p_pr = OxmlElement("w:pPr")
            p.insert(0, p_pr)
        if is_rtl:
            bidi_el = OxmlElement("w:bidi")
            p_pr.append(bidi_el)


def configure_epub_for_language(
    css: str, language: str = "en"
) -> str:
    """Extend or modify CSS for language-specific typography.

    Args:
        css: Base CSS content.
        language: ISO 639 language code.

    Returns:
        CSS with language-specific additions.
    """
    lang_config = get_language_config(language)

    additions = []

    if lang_config.script == ScriptType.RTL:
        additions.append(
            f"body {{\n"
            f"  direction: rtl;\n"
            f"  unicode-bidi: embed;\n"
            f"  font-family: {lang_config.font_family};\n"
            f"  font-size: {lang_config.font_size}pt;\n"
            f"  line-height: {lang_config.line_height};\n"
            f"}}\n"
        )

    if lang_config.script == ScriptType.CJK:
        additions.append(
            f"body {{\n"
            f"  font-family: {lang_config.font_family};\n"
            f"  font-size: {lang_config.font_size}pt;\n"
            f"  line-height: {lang_config.line_height};\n"
            f"}}\n"
        )
        additions.append(
            "p {\n"
            "  text-indent: 2em;\n"
            "}\n"
        )

    if not additions:
        return css

    return css + "\n/* Language-specific overrides */\n" + "".join(additions)


def configure_latex_for_language(
    preamble: str, language: str = "en"
) -> str:
    """Extend or modify LaTeX preamble for language-specific typesetting.

    Args:
        preamble: Base LaTeX preamble content.
        language: ISO 639 language code.

    Returns:
        LaTeX preamble with language-specific packages.
    """
    lang_config = get_language_config(language)
    additions = []

    if lang_config.script == ScriptType.RTL:
        additions.append(
            r"\usepackage[arabic,english]{babel}" + "\n"
            r"\babelprovide[import, main]{arabic}" + "\n"
        )
        if language == "he":
            additions.append(
                r"\usepackage[hebrew,english]{babel}" + "\n"
                r"\babelprovide[import, main]{hebrew}" + "\n"
            )

    if lang_config.script == ScriptType.CJK:
        if language.startswith("zh"):
            additions.append(r"\usepackage[UTF8]{ctex}" + "\n")
        elif language == "ja":
            additions.append(r"\usepackage[utf8]{inputenc}" + "\n")
            additions.append(r"\usepackage{luatexja}" + "\n")

    if not additions:
        return preamble

    # Insert before \begin{document} (which is in the preamble)
    return preamble + "".join(additions)
