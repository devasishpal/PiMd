"""Tests for internationalisation (i18n) support."""

from __future__ import annotations

from pimd.i18n import (
    ScriptType,
    detect_script,
    get_language_config,
    is_cjk_language,
    is_rtl_language,
    process_text_for_language,
)


class TestScriptDetection:
    def test_detect_latin(self) -> None:
        assert detect_script("Hello World") == ScriptType.LTR

    def test_detect_arabic(self) -> None:
        assert detect_script("مرحبا بالعالم") == ScriptType.RTL

    def test_detect_hebrew(self) -> None:
        assert detect_script("שלום עולם") == ScriptType.RTL

    def test_detect_persian(self) -> None:
        assert detect_script("سلام دنیا") == ScriptType.RTL

    def test_detect_urdu(self) -> None:
        assert detect_script("ہیلو دنیا") == ScriptType.RTL

    def test_detect_chinese(self) -> None:
        assert detect_script("你好世界") == ScriptType.CJK

    def test_detect_japanese(self) -> None:
        assert detect_script("こんにちは世界") == ScriptType.CJK

    def test_detect_korean(self) -> None:
        assert detect_script("안녕하세요 세계") == ScriptType.CJK

    def test_detect_empty(self) -> None:
        assert detect_script("") == ScriptType.NEUTRAL

    def test_detect_mixed_rtl_ltr(self) -> None:
        # Mixed content — RTL should dominate if >30% of chars
        text = "Hello " + "مرحبا" + " world"
        assert detect_script(text) == ScriptType.RTL

    def test_detect_mixed_cjk_ltr(self) -> None:
        text = "Hello " + "你好" + " world"
        assert detect_script(text) == ScriptType.CJK


class TestRtlLanguage:
    def test_arabic(self) -> None:
        assert is_rtl_language("ar")

    def test_arabic_with_region(self) -> None:
        assert is_rtl_language("ar-SA")

    def test_persian(self) -> None:
        assert is_rtl_language("fa")

    def test_urdu(self) -> None:
        assert is_rtl_language("ur")

    def test_hebrew(self) -> None:
        assert is_rtl_language("he")

    def test_english_not_rtl(self) -> None:
        assert not is_rtl_language("en")

    def test_french_not_rtl(self) -> None:
        assert not is_rtl_language("fr")


class TestCjkLanguage:
    def test_chinese(self) -> None:
        assert is_cjk_language("zh")

    def test_chinese_with_region(self) -> None:
        assert is_cjk_language("zh-CN")

    def test_japanese(self) -> None:
        assert is_cjk_language("ja")

    def test_korean(self) -> None:
        assert is_cjk_language("ko")

    def test_english_not_cjk(self) -> None:
        assert not is_cjk_language("en")


class TestLanguageConfig:
    def test_english_config(self) -> None:
        config = get_language_config("en")
        assert config.script == ScriptType.LTR
        assert config.language == "en"
        assert "serif" in config.font_family

    def test_arabic_config(self) -> None:
        config = get_language_config("ar")
        assert config.script == ScriptType.RTL
        assert config.font_size == 12

    def test_chinese_config(self) -> None:
        config = get_language_config("zh")
        assert config.script == ScriptType.CJK

    def test_japanese_config(self) -> None:
        config = get_language_config("ja")
        assert config.script == ScriptType.CJK

    def test_hebrew_config(self) -> None:
        config = get_language_config("he")
        assert config.script == ScriptType.RTL

    def test_unknown_language_falls_back(self) -> None:
        config = get_language_config("xx")
        assert config.script == ScriptType.LTR
        assert config.language == "en"

    def test_rtl_language_without_preset(self) -> None:
        # RTL language that has no explicit config should still be detected as RTL
        config = get_language_config("ps")  # Pashto — RTL but no preset
        assert config.script == ScriptType.RTL

    def test_language_config_has_font_size(self) -> None:
        config = get_language_config("en")
        assert config.font_size > 0

    def test_language_config_has_line_height(self) -> None:
        config = get_language_config("en")
        assert config.line_height > 0

    def test_language_config_has_paragraph_spacing(self) -> None:
        config = get_language_config("en")
        assert config.paragraph_spacing >= 0


class TestTextProcessing:
    def test_process_latin_text(self) -> None:
        result = process_text_for_language("Hello World", "en")
        assert result == "Hello World"

    def test_process_arabic_text_no_deps(self) -> None:
        # Without arabic_reshaper, text passes through unchanged
        text = "مرحبا"
        result = process_text_for_language(text, "ar")
        assert isinstance(result, str)

    def test_configure_epub_for_language(self) -> None:
        from pimd.i18n import configure_epub_for_language

        css = "body { margin: 0; }"
        rtl_css = configure_epub_for_language(css, "ar")
        assert "direction: rtl" in rtl_css
        assert css in rtl_css

        cjk_css = configure_epub_for_language(css, "zh")
        assert "text-indent: 2em" in cjk_css

        ltr_css = configure_epub_for_language(css, "en")
        assert ltr_css == css  # No additions for LTR

    def test_configure_latex_for_language(self) -> None:
        from pimd.i18n import configure_latex_for_language

        preamble = r"\documentclass{article}"
        arabic_preamble = configure_latex_for_language(preamble, "ar")
        assert "babel" in arabic_preamble

        cjk_preamble = configure_latex_for_language(preamble, "zh")
        assert "ctex" in cjk_preamble

        english_preamble = configure_latex_for_language(preamble, "en")
        assert english_preamble == preamble  # No changes for LTR


class TestLanguageConfigsCompleteness:
    def test_all_presets_have_required_fields(self) -> None:
        from pimd.i18n import LANGUAGE_CONFIGS

        for lang, config in LANGUAGE_CONFIGS.items():
            assert config.language == lang
            assert isinstance(config.script, ScriptType)
            assert config.font_family
            assert config.font_size > 0
            assert config.line_height > 0
            assert config.paragraph_spacing >= 0

    def test_rtl_presets_have_correct_script(self) -> None:
        from pimd.i18n import LANGUAGE_CONFIGS

        for lang, config in LANGUAGE_CONFIGS.items():
            if is_rtl_language(lang):
                assert config.script == ScriptType.RTL, f"{lang} should be RTL"

    def test_cjk_presets_have_correct_script(self) -> None:
        from pimd.i18n import LANGUAGE_CONFIGS

        for lang, config in LANGUAGE_CONFIGS.items():
            if is_cjk_language(lang):
                assert config.script == ScriptType.CJK, f"{lang} should be CJK"
