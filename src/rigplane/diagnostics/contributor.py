"""Diagnostic contributor protocol and bundle context."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class DiagnosticContributor(Protocol):
    """A pluggable source of diagnostic data.

    Discovered by the bundle generator via setuptools entry points
    (``rigplane.diagnostics`` group) or runtime ``register()``.

    Implementations should be cheap to instantiate (no heavy work in
    ``__init__``) and idempotent on ``contribute()``.
    """

    name: str

    def contribute(self, ctx: BundleContext, output_dir: Path) -> None:
        """Write diagnostic data files into ``output_dir``.

        May raise on recoverable failure; the bundler logs to
        ``manifest.warnings`` and continues with other contributors.
        """


@dataclass(frozen=True)
class BundleContext:
    """Read-only context handed to every contributor.

    ``radio`` is typed as ``Any | None`` to avoid a circular import
    between ``rigplane.diagnostics`` and ``rigplane.runtime`` /
    ``rigplane.radio_protocol``. Contributors that need radio-specific
    behaviour do ``isinstance(ctx.radio, AudioCapable)`` themselves.
    """

    radio: Any | None
    config_dir: Path
    log_dir: Path
    user_description: str | None
    issue_ref: str | None
    contact_email: str | None
    contact_callsign: str | None
    submission_id: str
    generated_at_unix: int
