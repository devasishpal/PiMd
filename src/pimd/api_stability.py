"""API stability markers — every public API must declare its lifecycle status.

Usage::

    from pimd.api_stability import stable, beta, experimental, deprecated

    @stable("2.0")
    def render(source: str) -> RenderResult:
        ...

    @beta("2.3")
    class StreamingRenderer:
        ...

    @experimental("3.0")
    class AIDiagramGenerator:
        ...

    @deprecated("2.0", removal="3.0", alternative="render()")
    def old_render(source: str):
        ...
"""

from __future__ import annotations

import enum
import functools
import inspect
import warnings
from collections.abc import Callable
from typing import Any, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


class ApiStatus(enum.Enum):
    STABLE = "stable"
    BETA = "beta"
    EXPERIMENTAL = "experimental"
    DEPRECATED = "deprecated"
    INTERNAL = "internal"


_EMOJI: dict[ApiStatus, str] = {
    ApiStatus.STABLE: "",
    ApiStatus.BETA: "",
    ApiStatus.EXPERIMENTAL: "",
    ApiStatus.DEPRECATED: "",
    ApiStatus.INTERNAL: "",
}


def stable(since: str) -> Callable[[F], F]:
    """Mark a public API as **stable** — guaranteed backward compatible.

    Args:
        since: Version string when this API became stable (e.g. ``"2.0"``).
    """
    def decorator(obj: F) -> F:
        _attach_status(obj, ApiStatus.STABLE, since=since)
        return obj
    return decorator


def beta(since: str) -> Callable[[F], F]:
    """Mark a public API as **beta** — stable API shape, may gain parameters.

    Args:
        since: Version string when this API entered beta.
    """
    def decorator(obj: F) -> F:
        _attach_status(obj, ApiStatus.BETA, since=since)
        return obj
    return decorator


def experimental(since: str) -> Callable[[F], F]:
    """Mark a public API as **experimental** — may change or be removed.

    Args:
        since: Version string when this API was introduced.
    """
    def decorator(obj: F) -> F:
        _attach_status(obj, ApiStatus.EXPERIMENTAL, since=since)
        return obj
    return decorator


def deprecated(
    since: str,
    removal: str = "",
    alternative: str = "",
) -> Callable[[F], F]:
    """Mark a public API as **deprecated** — emits ``DeprecationWarning``.

    Args:
        since: Version when deprecation started.
        removal: Version when the API will be removed (e.g. ``"4.0"``).
        alternative: Recommended replacement (e.g. ``"use render() instead"``).

    Usage::

        @deprecated("2.0", removal="3.0", alternative="render()")
        def old_render(source):
            ...
    """
    def decorator(obj: F) -> F:
        _attach_status(obj, ApiStatus.DEPRECATED, since=since, removal=removal, alternative=alternative)

        if inspect.isclass(obj):
            # Wrap __init__ to warn on instantiation
            orig_init = obj.__init__

            @functools.wraps(orig_init)
            def _new_init(self, *args: Any, **kwargs: Any) -> None:
                _emit_deprecation(obj.__name__, since, removal, alternative)
                orig_init(self, *args, **kwargs)
            obj.__init__ = _new_init  # type: ignore
            return obj

        @functools.wraps(obj)
        def _wrapper(*args: Any, **kwargs: Any) -> Any:
            _emit_deprecation(obj.__name__, since, removal, alternative)
            return obj(*args, **kwargs)
        return _wrapper  # type: ignore
    return decorator


def internal() -> Callable[[F], F]:
    """Mark a public API as **internal** — no compatibility guarantees.

    Internal APIs may change without notice. They are exposed only for
    advanced use-cases and debugging.
    """
    def decorator(obj: F) -> F:
        _attach_status(obj, ApiStatus.INTERNAL)
        return obj
    return decorator


def get_api_status(obj: Any) -> ApiStatus | None:
    """Return the :class:`ApiStatus` of *obj*, or ``None`` if unmarked."""
    return getattr(obj, "__api_status__", None)


def get_api_since(obj: Any) -> str:
    """Return the version string when *obj* was introduced."""
    return getattr(obj, "__api_since__", "")


def get_api_removal(obj: Any) -> str:
    """Return the version when *obj* will be removed (deprecated only)."""
    return getattr(obj, "__api_removal__", "")


def get_api_alternative(obj: Any) -> str:
    """Return the recommended alternative (deprecated only)."""
    return getattr(obj, "__api_alternative__", "")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _attach_status(
    obj: F,
    status: ApiStatus,
    since: str = "",
    removal: str = "",
    alternative: str = "",
) -> None:
    obj.__api_status__ = status  # type: ignore
    obj.__api_since__ = since  # type: ignore
    if status == ApiStatus.DEPRECATED:
        obj.__api_removal__ = removal  # type: ignore
        obj.__api_alternative__ = alternative  # type: ignore


def _emit_deprecation(name: str, since: str, removal: str, alternative: str) -> None:
    msg = f"{name!r} was deprecated in v{since}"
    if removal:
        msg += f" and will be removed in v{removal}"
    if alternative:
        msg += f". Use {alternative} instead."
    warnings.warn(msg, DeprecationWarning, stacklevel=3)
