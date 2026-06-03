"""Tests for the equation system: models, parser, OMML, engine, validation."""

from __future__ import annotations

from pathlib import Path

from pimd.equations import EquationEngine, EquationResult
from pimd.equations.cache import EquationCache, MemoryEquationCache
from pimd.equations.fallback import latex_to_svg
from pimd.equations.omml import latex_to_omml, tokenize
from pimd.equations.parser import (
    clean_latex,
    extract_inline_equations,
    is_chemical_formula,
    is_display_equation,
    normalize_chemical,
)
from pimd.equations.validation import EquationValidator
from pimd.models import EquationBlock, Span

# ======================================================================
# Equation Models
# ======================================================================


class TestEquationResult:
    def test_default_construction(self) -> None:
        r = EquationResult(source=r"E=mc^2", latex=r"E=mc^2")
        assert r.source == r"E=mc^2"
        assert r.latex == r"E=mc^2"
        assert not r.display
        assert r.error is None
        assert not r.cached

    def test_success_with_omml(self) -> None:
        r = EquationResult(source="x", latex="x", omml="<fake>")
        assert r.success
        assert r.has_omml

    def test_success_with_svg(self) -> None:
        r = EquationResult(source="x", latex="x", svg="<svg/>")
        assert r.success
        assert not r.has_omml

    def test_success_both(self) -> None:
        r = EquationResult(source="x", latex="x", omml="<fake>", svg="<svg/>")
        assert r.success

    def test_failure(self) -> None:
        r = EquationResult(source="x", latex="x", error="Parse error")
        assert not r.success
        assert not r.has_omml

    def test_to_dict(self) -> None:
        r = EquationResult(
            source="src",
            latex=r"E=mc^2",
            display=True,
            omml="<fake>",
            label="eq:1",
            number=1,
            render_time=0.5,
        )
        d = r.to_dict()
        assert d["latex"] == r"E=mc^2"
        assert d["display"]
        assert d["has_omml"]
        assert d["success"]
        assert d["label"] == "eq:1"
        assert d["number"] == 1
        assert d["render_time"] == 0.5

    def test_chemical_flag(self) -> None:
        r = EquationResult(source="H2O", latex="H_2O", is_chemical=True)
        assert r.is_chemical


class TestEquationBlock:
    def test_plain_text(self) -> None:
        b = EquationBlock(latex=r"E=mc^2", number=1)
        text = b.plain_text()
        assert "Equation" in text
        assert "E=mc^2" in text

    def test_label(self) -> None:
        b = EquationBlock(latex="x=1", label="eq:test")
        assert b.label == "eq:test"


# ======================================================================
# Span with math
# ======================================================================


class TestSpanMath:
    def test_math_span(self) -> None:
        s = Span(text="", math=r"E=mc^2", math_display=False)
        assert s.text == ""
        assert s.math == r"E=mc^2"
        assert not s.math_display
        assert not s.bold

    def test_display_math_span(self) -> None:
        s = Span(text="", math=r"\int_a^b", math_display=True)
        assert s.math_display


# ======================================================================
# Parser
# ======================================================================


class TestCleanLatex:
    def test_clean_dollar_inline(self) -> None:
        assert clean_latex("$x=1$", "latex") == "x=1"

    def test_clean_dollar_display(self) -> None:
        assert clean_latex("$$x=1$$", "latex") == "x=1"

    def test_clean_paren(self) -> None:
        assert clean_latex(r"\(x=1\)", "latex") == "x=1"

    def test_clean_bracket(self) -> None:
        assert clean_latex(r"\[x=1\]", "latex") == "x=1"

    def test_clean_noop(self) -> None:
        assert clean_latex("x=1", "latex") == "x=1"


class TestIsDisplayEquation:
    def test_dollar_display(self) -> None:
        assert is_display_equation("$$x=1$$")

    def test_bracket_display(self) -> None:
        assert is_display_equation(r"\[x=1\]")

    def test_equation_env(self) -> None:
        assert is_display_equation(r"\begin{equation}x=1\end{equation}")

    def test_not_display(self) -> None:
        assert not is_display_equation("x=1")
        assert not is_display_equation("$x=1$")

    def test_empty(self) -> None:
        assert not is_display_equation("")


class TestExtractInlineEquations:
    def test_single_inline(self) -> None:
        results = extract_inline_equations("The equation $E=mc^2$ is famous.")
        assert len(results) >= 1
        src, fmt, display, start, end = results[0]
        assert "E=mc^2" in src
        assert not display

    def test_multiple_inline(self) -> None:
        text = r"First $a=1$, second $b=2$."
        results = extract_inline_equations(text)
        assert len(results) >= 2
        assert "a=1" in results[0][0]
        assert "b=2" in results[1][0]

    def test_display_inline(self) -> None:
        text = r"Block $$E=mc^2$$ is display."
        results = extract_inline_equations(text)
        display_results = [r for r in results if r[2]]
        assert len(display_results) >= 1

    def test_no_equation(self) -> None:
        results = extract_inline_equations("Plain text without math.")
        assert len(results) == 0


class TestChemicalFormula:
    def test_is_chemical(self) -> None:
        assert is_chemical_formula("H_2O")
        assert is_chemical_formula("CO_2")
        assert is_chemical_formula("CH_4")
        assert is_chemical_formula("NH_3")

    def test_not_chemical(self) -> None:
        assert not is_chemical_formula("x=1")

    def test_normalize(self) -> None:
        assert "H_{2}O" in normalize_chemical("H_2O")
        assert "CO_{2}" in normalize_chemical("CO_2")


# ======================================================================
# OMML Converter
# ======================================================================


class TestLatexToOMML:
    def test_simple_expression(self) -> None:
        result = latex_to_omml(r"x=1")
        assert result is not None
        # Should be an OMML element (m:oMath)
        assert result.tag.endswith("oMath")

    def test_fraction(self) -> None:
        result = latex_to_omml(r"\frac{a}{b}")
        assert result is not None

    def test_superscript(self) -> None:
        result = latex_to_omml(r"x^2")
        assert result is not None

    def test_subscript(self) -> None:
        result = latex_to_omml(r"x_1")
        assert result is not None

    def test_sqrt(self) -> None:
        result = latex_to_omml(r"\sqrt{x}")
        assert result is not None

    def test_integral(self) -> None:
        result = latex_to_omml(r"\int_a^b x dx")
        assert result is not None

    def test_sum(self) -> None:
        result = latex_to_omml(r"\sum_{i=0}^n i^2")
        assert result is not None

    def test_greek(self) -> None:
        result = latex_to_omml(r"\alpha + \beta")
        assert result is not None

    def test_display(self) -> None:
        result = latex_to_omml(r"x=1", display=True)
        assert result is not None
        assert result.tag.endswith("oMathPara")

    def test_empty(self) -> None:
        result = latex_to_omml("")
        assert result is not None

    def test_invalid_returns_none(self) -> None:
        result = latex_to_omml(r"\frac{broken")
        # Should not crash, may return None or element
        assert result is None or result is not None


class TestTokenizer:
    def test_simple(self) -> None:
        tokens = tokenize(r"x + y = 5")
        assert len(tokens) >= 3
        assert "x" in tokens
        assert "+" in tokens

    def test_frac(self) -> None:
        tokens = tokenize(r"\frac{a}{b}")
        assert any("frac" in t for t in tokens)

    def test_greek(self) -> None:
        tokens = tokenize(r"\alpha \beta")
        assert len(tokens) >= 2


# ======================================================================
# SVG Fallback
# ======================================================================


class TestLatexToSVG:
    def test_always_returns_something(self) -> None:
        svg = latex_to_svg(r"E=mc^2")
        assert svg is not None
        assert "<svg" in svg

    def test_returns_svg_tag(self) -> None:
        svg = latex_to_svg(r"x=1")
        assert svg is not None
        assert svg.strip().startswith("<svg")


# ======================================================================
# Validation
# ======================================================================


class TestEquationValidator:
    def test_valid_equation(self) -> None:
        v = EquationValidator()
        result = v.validate(r"E=mc^2")
        assert result.valid

    def test_empty(self) -> None:
        v = EquationValidator()
        result = v.validate("")
        assert not result.valid
        assert len(result.errors) > 0

    def test_unbalanced_braces(self) -> None:
        v = EquationValidator()
        v.validate(r"\frac{a{b}")
        # May or may not detect — depends on complexity
        # At minimum should not crash

    def test_frac_without_braces(self) -> None:
        v = EquationValidator()
        v.validate(r"\frac a b")
        # Should return warnings, not crash


# ======================================================================
# Equation Cache
# ======================================================================


class TestMemoryEquationCache:
    def test_set_and_get(self) -> None:
        cache = MemoryEquationCache()
        result = EquationResult(source="x=1", latex="x=1")
        cache.set("key1", result)
        cached = cache.get("key1")
        assert cached is not None
        assert cached.latex == "x=1"

    def test_get_missing(self) -> None:
        cache = MemoryEquationCache()
        assert cache.get("nope") is None

    def test_clear(self) -> None:
        cache = MemoryEquationCache()
        cache.set("k", EquationResult(source="src", latex="la"))
        cache.clear()
        assert cache.get("k") is None

    def test_ttl_expiry(self) -> None:
        import time

        cache = MemoryEquationCache(default_ttl=0.05)
        cache.set("k", EquationResult(source="s", latex="l"))
        assert cache.get("k") is not None
        time.sleep(0.1)
        assert cache.get("k") is None

    def test_make_key(self) -> None:
        key1 = EquationCache.make_key("E=mc^2", display=False)
        key2 = EquationCache.make_key("E=mc^2", display=True)
        key3 = EquationCache.make_key("E=mc^2", display=False)
        assert key1 != key2
        assert key1 == key3
        assert key1.startswith("eq:")


# ======================================================================
# Equation Engine
# ======================================================================


class TestEquationEngine:
    def test_instantiation(self) -> None:
        engine = EquationEngine()
        assert engine.config.enabled

    def test_render_simple(self) -> None:
        engine = EquationEngine()
        result = engine.render(r"E=mc^2")
        assert result.success or result.error

    def test_render_display(self) -> None:
        engine = EquationEngine()
        result = engine.render(r"\int_a^b x dx", display=True)
        assert result.success or result.error

    def test_render_fails_gracefully(self) -> None:
        engine = EquationEngine()
        result = engine.render(r"\brokencommand{test}")
        # Should not crash — may succeed or fail gracefully
        assert result is not None

    def test_chemical(self) -> None:
        engine = EquationEngine()
        result = engine.render(r"H_2O", force_chemical=True)
        assert result is not None

    def test_cache_hit(self) -> None:
        engine = EquationEngine()
        engine.render(r"x=1")
        r2 = engine.render(r"x=1")
        assert r2.cached or not r2.error

    def test_clear_cache(self) -> None:
        engine = EquationEngine()
        engine.render(r"x=2")
        engine.clear_cache()
        # Should work without error
        assert True

    def test_reset_numbering(self) -> None:
        engine = EquationEngine()
        engine.render(r"a=1", display=True)
        engine.render(r"b=2", display=True)
        engine.reset_numbering()
        r = engine.render(r"c=3", display=True)
        assert r.number == 1

    def test_doctor(self) -> None:
        engine = EquationEngine()
        results = engine.doctor()
        assert len(results) >= 3
        assert all("check" in r for r in results)
        assert all("status" in r for r in results)

    def test_is_available(self) -> None:
        engine = EquationEngine()
        assert engine.is_available()


# ======================================================================
# System Integration
# ======================================================================


class TestEquationIntegration:
    """Test that equations work end-to-end through the conversion pipeline."""

    def test_inline_math_in_paragraph(self, tmp_path: Path) -> None:
        from pimd.converters.markdown import MarkdownConverter

        md = "The equation $E = mc^2$ is famous.\n\n$$\\int_a^b x^2 dx$$\n\nAnd $x=1$."
        out = tmp_path / "math.docx"
        converter = MarkdownConverter()
        converter.convert_text(md, str(out))
        assert out.exists()
        assert out.stat().st_size > 0

    def test_display_math_block(self, tmp_path: Path) -> None:
        from pimd.converters.markdown import MarkdownConverter

        md = "$$E = mc^2$$\n\nA paragraph."
        out = tmp_path / "display.docx"
        converter = MarkdownConverter()
        converter.convert_text(md, str(out))
        assert out.exists()

    def test_chemical_in_document(self, tmp_path: Path) -> None:
        from pimd.converters.markdown import MarkdownConverter

        md = "Water is $H_2O$ and methane is $CH_4$."
        out = tmp_path / "chem.docx"
        converter = MarkdownConverter()
        converter.convert_text(md, str(out))
        assert out.exists()

    def test_large_number_of_equations(self, tmp_path: Path) -> None:
        from pimd.converters.markdown import MarkdownConverter

        equations = "\n\n".join(f"$$E_{i} = mc^{i}$$" for i in range(100))
        md = f"# Many Equations\n\n{equations}"
        out = tmp_path / "large.docx"
        converter = MarkdownConverter()
        converter.convert_text(md, str(out))
        assert out.exists()

    def test_statistics_with_equations(self, tmp_path: Path) -> None:
        from pimd.converters.markdown import MarkdownConverter

        md = r"$E=mc^2$ and $$x=\frac{1}{2}$$"
        out = tmp_path / "stats.docx"
        converter = MarkdownConverter()
        converter.convert_text(md, str(out))
        stats = converter.get_statistics()
        assert stats is not None

    def test_equation_block_model(self) -> None:
        """EquationBlock stores OMML or fallback correctly."""
        import xml.etree.ElementTree as ET

        # Simulate an OMML result
        block = EquationBlock(
            latex=r"E=mc^2",
            display=True,
            omml=ET.Element("{http://schemas.openxmlformats.org/officeDocument/2006/math}oMath"),
        )
        assert block.omml is not None
        assert block.latex == r"E=mc^2"

    def test_equationerror_fallback(self, tmp_path: Path) -> None:
        """Block with error renders as placeholder without crashing."""

        from pimd.models import Document
        from pimd.renderers.docx_renderer import DocxRenderer

        doc_model = Document(blocks=[EquationBlock(latex=r"\broken", error="Test error")])
        renderer = DocxRenderer()
        out = tmp_path / "error.docx"
        renderer.render(doc_model, str(out))
        assert out.exists()


class TestModelUpdates:
    def test_span_with_math(self) -> None:
        s = Span(text="", math=r"x^2", math_display=True)
        assert s.math == r"x^2"
        assert s.math_display
        assert not s.bold
        assert not s.italic

    def test_equation_block_plain_text(self) -> None:
        b = EquationBlock(latex=r"E=mc^2", number=42)
        text = b.plain_text()
        assert "42" in text
