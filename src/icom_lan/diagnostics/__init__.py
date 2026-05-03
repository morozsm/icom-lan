"""icom-lan diagnostic infrastructure (logging, contributors, bundle, upload).

Subsequent issues (#1388-#1401) build on this package.
"""

from icom_lan.diagnostics._discovery import discover, register
from icom_lan.diagnostics._logging import (
    SafeRotatingFileHandler,
    configure_diagnostic_logging,
)
from icom_lan.diagnostics.contributor import BundleContext, DiagnosticContributor
from icom_lan.diagnostics.redaction import (
    REDACTORS,
    redact_credentials,
    redact_ips,
    redact_paths,
    redact_tokens,
)

__all__ = [
    "REDACTORS",
    "BundleContext",
    "DiagnosticContributor",
    "SafeRotatingFileHandler",
    "configure_diagnostic_logging",
    "discover",
    "redact_credentials",
    "redact_ips",
    "redact_paths",
    "redact_tokens",
    "register",
]
