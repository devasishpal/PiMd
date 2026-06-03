"""Equation validation — detect malformed equations, graceful recovery."""

from __future__ import annotations

import re


class EquationValidationResult:
    """Result of validating an equation string."""

    def __init__(self) -> None:
        self.valid: bool = True
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def add_error(self, msg: str) -> None:
        self.valid = False
        self.errors.append(msg)

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)

    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
        }


class EquationValidator:
    """Validate LaTeX equation strings for common errors."""

    UNMATCHED_OPEN = re.compile(r"(?<!\\)\{[^}]*$")
    UNMATCHED_CLOSE = re.compile(r"^[^{]*\}")
    UNBALANCED_BRACKETS = re.compile(r"[\[\]\(\)]")

    MALFORMED_PATTERNS: list[tuple[re.Pattern, str]] = [
        (re.compile(r"\\frac[^\{]"), r"\frac requires braces: \frac{num}{den}"),
        (re.compile(r"\\sqrt[^\{\[\(]"), r"\sqrt requires braces: \sqrt{x} or \sqrt[n]{x}"),
        (
            re.compile(r"\\int[\^\_](?![\{a-zA-Z])"),
            r"\int limits should be in braces: \int_{a}^{b}",
        ),
        (re.compile(r"\^\s*$|\_\s*$"), r"Dangling ^ or _ at end of expression"),
        (
            re.compile(
                r"\\left[^\(\{\[\|\\]",
            ),
            r"\left must be followed by delimiter",
        ),
        (
            re.compile(
                r"\\right[^\)\}\]\|\\]",
            ),
            r"\right must be followed by delimiter",
        ),
    ]

    def validate(self, latex: str) -> EquationValidationResult:
        result = EquationValidationResult()

        # Empty check
        stripped = latex.strip()
        if not stripped:
            result.add_error("Empty equation string")
            return result

        # Brace balance
        brace_depth = 0
        for i, ch in enumerate(stripped):
            if ch == "{":
                brace_depth += 1
            elif ch == "}":
                brace_depth -= 1
                if brace_depth < 0:
                    context = stripped[max(0, i - 20) : i + 10]
                    result.add_error(f"Unmatched closing brace at position {i}: ...{context}...")
                    break

        if brace_depth > 0:
            result.add_warning(f"{brace_depth} unclosed brace(s) at end of expression")

        # Known patterns
        for pattern, msg in self.MALFORMED_PATTERNS:
            match = pattern.search(stripped)
            if match:
                result.add_warning(f"{msg} (found: '{match.group()[:30]}')")

        return result
