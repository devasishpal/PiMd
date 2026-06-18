"""Tests for pimd.api_stability — API lifecycle decorators."""

from __future__ import annotations

import warnings

import pytest

from pimd.api_stability import (
    ApiStatus,
    beta,
    deprecated,
    experimental,
    get_api_alternative,
    get_api_removal,
    get_api_since,
    get_api_status,
    internal,
    stable,
)


class TestApiStability:
    def test_stable_decorator(self) -> None:
        @stable("2.0")
        def foo() -> str:
            return "ok"

        assert get_api_status(foo) == ApiStatus.STABLE
        assert get_api_since(foo) == "2.0"
        assert foo() == "ok"

    def test_beta_decorator(self) -> None:
        @beta("2.1")
        def bar() -> int:
            return 42

        assert get_api_status(bar) == ApiStatus.BETA
        assert get_api_since(bar) == "2.1"
        assert bar() == 42

    def test_experimental_decorator(self) -> None:
        @experimental("2.2")
        def baz() -> str:
            return "exp"

        assert get_api_status(baz) == ApiStatus.EXPERIMENTAL
        assert get_api_since(baz) == "2.2"
        assert baz() == "exp"

    def test_internal_decorator(self) -> None:
        @internal()
        def qux() -> str:
            return "internal"

        assert get_api_status(qux) == ApiStatus.INTERNAL
        assert qux() == "internal"

    def test_deprecated_function(self) -> None:
        @deprecated("2.0", removal="3.0", alternative="new_func()")
        def old_func() -> int:
            return 99

        assert get_api_status(old_func) == ApiStatus.DEPRECATED
        assert get_api_since(old_func) == "2.0"
        assert get_api_removal(old_func) == "3.0"
        assert get_api_alternative(old_func) == "new_func()"

        with pytest.warns(DeprecationWarning, match="old_func"):
            result = old_func()
        assert result == 99

    def test_deprecated_class(self) -> None:
        @deprecated("2.1", removal="4.0", alternative="NewClass")
        class OldClass:
            def __init__(self) -> None:
                self.value = 42

        with pytest.warns(DeprecationWarning, match="OldClass"):
            obj = OldClass()
        assert obj.value == 42

    def test_no_warning_on_stable(self) -> None:
        @stable("2.0")
        def safe() -> str:
            return "safe"

        with warnings.catch_warnings():
            warnings.simplefilter("error")
            result = safe()
        assert result == "safe"

    def test_get_api_status_unmarked(self) -> None:
        def unmarked() -> None:
            pass

        assert get_api_status(unmarked) is None
        assert get_api_since(unmarked) == ""
