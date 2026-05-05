"""Built-in diagnostic contributors.

#1390 ships: system, invocation, dependencies, config.
#1391 adds: radio, audio.
#1392 adds: logs, state, errors.
"""

from rigplane.diagnostics.contributors.audio import AudioContributor
from rigplane.diagnostics.contributors.config import ConfigContributor
from rigplane.diagnostics.contributors.dependencies import DependenciesContributor
from rigplane.diagnostics.contributors.errors import ErrorsContributor
from rigplane.diagnostics.contributors.invocation import InvocationContributor
from rigplane.diagnostics.contributors.logs import LogsContributor
from rigplane.diagnostics.contributors.radio import RadioContributor
from rigplane.diagnostics.contributors.state import StateContributor
from rigplane.diagnostics.contributors.system import SystemContributor

__all__ = [
    "AudioContributor",
    "ConfigContributor",
    "DependenciesContributor",
    "ErrorsContributor",
    "InvocationContributor",
    "LogsContributor",
    "RadioContributor",
    "StateContributor",
    "SystemContributor",
]
