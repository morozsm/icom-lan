"""Helpers for command-builder tests that want a stable IC-7610 target."""

from __future__ import annotations

from functools import partial, update_wrapper
import inspect
from types import ModuleType
from typing import Any

_SKIP_NAMES = {"build_civ_frame", "build_cmd29_frame"}


def _bind_builder(func: Any, *, to_addr: int) -> Any:
    """Bind a default CI-V target address for command builder call sites."""
    wrapped = partial(func, to_addr=to_addr)
    update_wrapper(wrapped, func)
    return wrapped


class CommandModuleProxy:
    """Proxy that injects ``to_addr`` into command-builder calls."""

    def __init__(self, module: ModuleType, *, to_addr: int) -> None:
        self._module = module
        self._to_addr = to_addr

    def __getattr__(self, name: str) -> Any:
        value = getattr(self._module, name)
        if name in _SKIP_NAMES:
            return value
        if callable(value):
            try:
                signature = inspect.signature(value)
            except (TypeError, ValueError):
                return value
            if "to_addr" in signature.parameters:
                return _bind_builder(value, to_addr=self._to_addr)
        return value


def bind_default_addr_module(module: ModuleType, *, to_addr: int) -> None:
    """Wrap command builders on the module so late imports see bound callables."""
    for name in dir(module):
        if name in _SKIP_NAMES:
            continue
        value = getattr(module, name, None)
        if not callable(value):
            continue
        try:
            signature = inspect.signature(value)
        except (TypeError, ValueError):
            continue
        if "to_addr" in signature.parameters:
            setattr(module, name, _bind_builder(value, to_addr=to_addr))


def bind_default_addr_globals(namespace: dict[str, Any], *, to_addr: int) -> None:
    """Wrap imported command builders in a test module namespace."""
    for name, value in list(namespace.items()):
        if isinstance(value, ModuleType) and value.__name__ == "icom_lan.commands":
            namespace[name] = CommandModuleProxy(value, to_addr=to_addr)
            continue
        if getattr(value, "__module__", None) != "icom_lan.commands":
            continue
        if not callable(value):
            continue
        if name in _SKIP_NAMES:
            continue
        try:
            signature = inspect.signature(value)
        except (TypeError, ValueError):
            continue
        if "to_addr" in signature.parameters:
            namespace[name] = _bind_builder(value, to_addr=to_addr)
