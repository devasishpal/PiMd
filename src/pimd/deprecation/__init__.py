"""Deprecation system — mark APIs as deprecated, emit warnings, ease migrations.

Usage::

    from pimd.deprecation import deprecated, deprecate_parameter

    class MyClass:
        @deprecated("Use new_method instead", version="0.4.0")
        def old_method(self):
            ...
"""

from __future__ import annotations

import functools
import warnings
from collections.abc import Callable
from typing import Any


class PiMDDeprecationWarning(DeprecationWarning):
    """Base warning for deprecated PiMD APIs."""


def deprecated(
    message: str = "",
    version: str = "",
    *,
    category: type[Warning] = PiMDDeprecationWarning,
) -> Callable[..., Any]:
    """Decorator: mark a function or class as deprecated.

    Args:
        message: Explanation / migration path.
        version: Version in which the API was deprecated.
        category: Warning class (default: PiMDDeprecationWarning).

    Usage::

        @deprecated("Use 'new_func' instead.", version="0.4.0")
        def old_func():
            pass
    """

    def decorator(obj: Any) -> Any:
        if isinstance(obj, type):
            return _deprecated_class(obj, message, version, category)
        if _is_async(obj):
            return _deprecated_async(obj, message, version, category)
        else:
            return _deprecated_func(obj, message, version, category)

    return decorator


def _deprecated_func(func: Any, message: str, version: str, category: type[Warning]) -> Any:
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        _emit_warning(func.__name__, message, version, category)
        return func(*args, **kwargs)

    return wrapper


def _deprecated_async(func: Any, message: str, version: str, category: type[Warning]) -> Any:
    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        _emit_warning(func.__name__, message, version, category)
        return await func(*args, **kwargs)

    return wrapper


def _deprecated_class(cls: Any, message: str, version: str, category: type[Warning]) -> Any:
    old_init = cls.__init__

    @functools.wraps(old_init)
    def new_init(self: Any, *args: Any, **kwargs: Any) -> None:
        _emit_warning(cls.__name__, message, version, category)
        old_init(self, *args, **kwargs)

    cls.__init__ = new_init
    return cls


def _emit_warning(name: str, message: str, version: str, category: type[Warning]) -> None:
    parts = [f"'{name}' is deprecated."]
    if version:
        parts.append(f" (deprecated in {version})")
    if message:
        parts.append(f" {message}")
    warnings.warn(" ".join(parts), category, stacklevel=3)


def _is_async(func: Any) -> bool:
    import inspect

    return inspect.iscoroutinefunction(func)


def deprecate_parameter(
    old_name: str,
    new_name: str,
    version: str = "",
    message: str = "",
    *,
    category: type[Warning] = PiMDDeprecationWarning,
) -> Callable[..., Any]:
    """Decorator: rename a function parameter with deprecation warning.

    Usage::

        @deprecate_parameter("old_arg", "new_arg", version="0.4.0")
        def my_func(new_arg=None):
            ...
    """

    def decorator(func: Any) -> Any:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if old_name in kwargs:
                _emit_warning(
                    f"Parameter '{old_name}'",
                    f"Use '{new_name}' instead. {message}",
                    version,
                    category,
                )
                if new_name not in kwargs:
                    kwargs[new_name] = kwargs.pop(old_name)
                else:
                    kwargs.pop(old_name)
            return func(*args, **kwargs)

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            if old_name in kwargs:
                _emit_warning(
                    f"Parameter '{old_name}'",
                    f"Use '{new_name}' instead. {message}",
                    version,
                    category,
                )
                if new_name not in kwargs:
                    kwargs[new_name] = kwargs.pop(old_name)
                else:
                    kwargs.pop(old_name)
            return await func(*args, **kwargs)

        if _is_async(func):
            return async_wrapper
        return wrapper

    return decorator


__all__ = [
    "deprecated",
    "deprecate_parameter",
    "PiMDDeprecationWarning",
]
