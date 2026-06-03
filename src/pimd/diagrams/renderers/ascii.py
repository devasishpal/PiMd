"""ASCII diagram renderer — pure Python, no external deps needed."""

from __future__ import annotations

from typing import Any

from pimd.diagrams.models import DiagramResult
from pimd.diagrams.renderers.base import DiagramRenderer


class AsciiRenderer(DiagramRenderer):
    """Render ASCII art diagrams to PNG using Pillow.

    Supports box-drawing characters, ASCII flow charts, tree structures,
    and simple architecture diagrams.

    Falls back gracefully if Pillow is not installed.
    """

    language = "ascii"
    name = "ASCII Diagram"
    version = "1.0.0"
    description = "Render ASCII art diagrams and box drawings to images"
    priority = 50

    def is_available(self) -> bool:
        try:
            import PIL  # noqa: F401

            return True
        except ImportError:
            return False

    def render(self, source: str, **options: Any) -> DiagramResult:
        if not self.is_available():
            return DiagramResult(
                source=source,
                language=self.language,
                error="Pillow is required for ASCII diagram rendering. "
                "Install with: pip install Pillow",
            )

        from PIL import Image, ImageDraw

        lines = source.splitlines()
        if not lines:
            return DiagramResult(
                source=source,
                language=self.language,
                error="Empty diagram source",
            )

        # Determine font
        font = self._get_font(options.get("font_size", 14))
        char_width, char_height = self._measure_font(font)

        # Calculate image dimensions
        max_line_len = max(len(line) for line in lines)
        padding = 20
        img_width = max_line_len * char_width + padding * 2
        img_height = len(lines) * char_height + padding * 2

        # Clamp to configurable max
        max_w = options.get("max_width", 2000)
        max_h = options.get("max_height", 2000)
        img_width = min(img_width, max_w)
        img_height = min(img_height, max_h)

        # Render
        img = Image.new("RGB", (img_width, img_height), "white")
        draw = ImageDraw.Draw(img)

        y = padding
        for line in lines:
            draw.text((padding, y), line, font=font, fill="black")
            y += char_height

        # Save to PNG bytes
        buf = __import__("io").BytesIO()
        img.save(buf, format="PNG", optimize=True)
        png = buf.getvalue()

        return DiagramResult(
            source=source,
            language=self.language,
            png=png,
            width=img_width,
            height=img_height,
        )

    # ------------------------------------------------------------------
    # Font helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_font(size: int) -> object:
        """Load a monospace font."""
        from PIL import ImageFont

        font_names = [
            "Consolas",
            "Courier New",
            "DejaVu Sans Mono",
            "Liberation Mono",
            "monospace",
        ]
        for name in font_names:
            try:
                return ImageFont.truetype(name, size)
            except OSError:
                continue
        return ImageFont.load_default()

    @staticmethod
    def _measure_font(font: object) -> tuple[int, int]:
        """Return approximate (char_width, char_height) for *font*."""
        from PIL import Image, ImageDraw

        test_img = Image.new("RGB", (100, 50), "white")
        test_draw = ImageDraw.Draw(test_img)
        bbox = test_draw.textbbox((0, 0), "W", font=font)
        char_width = bbox[2] - bbox[0] + 1
        char_height = bbox[3] - bbox[1] + 2
        return char_width, char_height
