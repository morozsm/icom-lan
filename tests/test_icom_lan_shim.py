"""Backwards-compatibility coverage for the ``icom_lan`` shim package.

After the v2.0.0 rebrand to ``rigplane``, the ``icom_lan`` import path
must keep working (with a one-time DeprecationWarning) so existing
v1.x user scripts don't break.

These tests use ``importlib.reload`` to retrigger the module-level
``warnings.warn`` call — Python only fires module-body code on the
first import per process.
"""

from __future__ import annotations

import importlib
import sys
import warnings


def _fresh_import_icom_lan():
    """Reload icom_lan after dropping it (and its rigplane-aliased
    submodules) from sys.modules so the shim re-runs from scratch.

    We deliberately do *not* drop rigplane itself — the goal is to
    re-execute the icom_lan shim body, not to reinitialise rigplane.
    """
    for _mod in [
        m for m in sys.modules if m == "icom_lan" or m.startswith("icom_lan.")
    ]:
        del sys.modules[_mod]
    return importlib.import_module("icom_lan")


class TestDeprecationWarning:
    def test_first_import_emits_deprecation(self) -> None:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            _fresh_import_icom_lan()
        deprecations = [w for w in caught if issubclass(w.category, DeprecationWarning)]
        assert len(deprecations) >= 1, "expected at least one DeprecationWarning"
        assert any("icom_lan" in str(w.message) for w in deprecations), (
            f"DeprecationWarning should mention 'icom_lan', got: "
            f"{[str(w.message) for w in deprecations]}"
        )

    def test_warning_mentions_rigplane_replacement(self) -> None:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            _fresh_import_icom_lan()
        msgs = [str(w.message) for w in caught]
        assert any("rigplane" in m for m in msgs), msgs


class TestPublicApi:
    def test_icom_lan_icomradio_is_rigplane_icomradio(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            import icom_lan
            import rigplane

        assert icom_lan.IcomRadio is rigplane.IcomRadio

    def test_runtime_radio_importable(self) -> None:
        """Canonical post-modularization path:
        ``from icom_lan.runtime.radio import IcomRadio``."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from icom_lan.runtime.radio import IcomRadio

        assert IcomRadio.__name__ == "IcomRadio"

    def test_legacy_icom_lan_radio_path(self) -> None:
        """Pre-modularization path (still aliased through rigplane.radio
        sys.modules shim): ``from icom_lan.radio import IcomRadio``."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from icom_lan.radio import IcomRadio

        assert IcomRadio.__name__ == "IcomRadio"

    def test_radio_protocol_importable(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from icom_lan import Radio

        assert Radio.__name__ == "Radio"

    def test_create_radio_importable(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from icom_lan import create_radio

        assert callable(create_radio)


class TestSubmoduleAliasing:
    def test_web_is_aliased_to_rigplane_web(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            import icom_lan.web
            import rigplane.web

        assert icom_lan.web is rigplane.web
        assert sys.modules["icom_lan.web"] is sys.modules["rigplane.web"]

    def test_runtime_is_aliased_to_rigplane_runtime(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            import icom_lan.runtime
            import rigplane.runtime

        assert icom_lan.runtime is rigplane.runtime

    def test_cli_is_aliased(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            import icom_lan.cli
            import rigplane.cli

        assert icom_lan.cli is rigplane.cli

    def test_commands_is_aliased(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            import icom_lan.commands
            import rigplane.commands

        assert icom_lan.commands is rigplane.commands

    def test_legacy_top_level_radio_aliased(self) -> None:
        """``icom_lan.radio`` should resolve through rigplane's own
        legacy ``rigplane.radio`` -> ``rigplane.runtime.radio`` shim."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            import icom_lan.radio
            import rigplane.radio

        assert icom_lan.radio is rigplane.radio
