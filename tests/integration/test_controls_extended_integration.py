"""Extended control API integration tests (backlog items 6-9)."""

from __future__ import annotations

import asyncio

import pytest

from icom_lan import IcomRadio
from icom_lan.exceptions import CommandError
from icom_lan.types import Mode


pytestmark = pytest.mark.integration


def _clamp_level(v: int, delta: int = 20) -> int:
    return max(0, min(255, v + delta))


class TestControlApiExtended:
    """Integration coverage for less-tested high-level control APIs."""

    async def test_data_mode_roundtrip(self, radio: IcomRadio) -> None:
        """Toggle DATA mode and restore original value."""
        try:
            original = await radio.get_data_mode()
        except Exception as e:
            pytest.skip(f"DATA mode not available: {e}")

        target = not original
        try:
            await radio.set_data_mode(target)
            await asyncio.sleep(0.1)
            actual = await radio.get_data_mode()
            assert actual is target, f"Expected DATA mode {target}, got {actual}"
            print(f"DATA mode set: {actual} ✓")
        finally:
            await radio.set_data_mode(original)
            restored = await radio.get_data_mode()
            assert restored is original
            print(f"DATA mode restored: {restored} ✓")

    async def test_rf_af_squelch_controls(self, radio: IcomRadio) -> None:
        """Validate RF/AF roundtrip and squelch command acceptance."""
        try:
            original_rf = await radio.get_rf_gain()
            original_af = await radio.get_af_level()
        except Exception as e:
            pytest.skip(f"RF/AF APIs not available: {e}")

        target_rf = _clamp_level(original_rf, 15 if original_rf < 240 else -15)
        target_af = _clamp_level(original_af, 15 if original_af < 240 else -15)

        try:
            await radio.set_rf_gain(target_rf)
            await asyncio.sleep(0.05)
            current_rf = await radio.get_rf_gain()
            assert abs(current_rf - target_rf) <= 3, (
                f"RF gain mismatch: expected ~{target_rf}, got {current_rf}"
            )

            await radio.set_af_level(target_af)
            await asyncio.sleep(0.05)
            current_af = await radio.get_af_level()
            assert abs(current_af - target_af) <= 3, (
                f"AF level mismatch: expected ~{target_af}, got {current_af}"
            )

            # Squelch has no public getter; verify command acceptance on range points.
            await radio.set_squelch(0)
            await radio.set_squelch(64)
            await radio.set_squelch(0)

            print(f"RF/AF/squelch controls ✓ (rf={current_rf}, af={current_af})")
        finally:
            await radio.set_rf_gain(original_rf)
            await radio.set_af_level(original_af)
            await radio.set_squelch(0)
            print("RF/AF restored ✓")

    async def test_nb_nr_ipplus_digisel_and_conflict(self, radio: IcomRadio) -> None:
        """Roundtrip NB/NR/IP+/DIGI-SEL and verify PREAMP conflict semantics."""
        try:
            original_nb = await radio.get_nb()
            original_nr = await radio.get_nr()
            original_ip = await radio.get_ip_plus()
            original_digisel = await radio.get_digisel()
            original_preamp = await radio.get_preamp()
        except Exception as e:
            pytest.skip(f"Frontend toggles not available: {e}")

        try:
            await radio.set_nb(not original_nb)
            await asyncio.sleep(0.05)
            assert await radio.get_nb() is (not original_nb)

            await radio.set_nr(not original_nr)
            await asyncio.sleep(0.05)
            assert await radio.get_nr() is (not original_nr)

            await radio.set_ip_plus(not original_ip)
            await asyncio.sleep(0.05)
            assert await radio.get_ip_plus() is (not original_ip)

            await radio.set_digisel(not original_digisel)
            await asyncio.sleep(0.05)
            assert await radio.get_digisel() is (not original_digisel)

            # PREAMP and DIGI-SEL are mutually exclusive on IC-7610.
            await radio.set_digisel(True)
            with pytest.raises(CommandError):
                await radio.set_preamp(1 if original_preamp != 1 else 2)

            print("NB/NR/IP+/DIGI-SEL toggles + conflict check ✓")
        finally:
            try:
                await radio.set_digisel(False)
            except Exception:
                pass
            try:
                await radio.set_preamp(original_preamp)
            except Exception:
                pass
            await radio.set_nb(original_nb)
            await radio.set_nr(original_nr)
            await radio.set_ip_plus(original_ip)
            await radio.set_digisel(original_digisel)
            print("Frontend toggles restored ✓")

    async def test_snapshot_restore_roundtrip(self, radio: IcomRadio) -> None:
        """Modify multiple knobs and validate snapshot_state/restore_state."""
        snapshot = await radio.snapshot_state()
        required = {"frequency", "mode", "power"}
        if not required.issubset(snapshot.keys()):
            pytest.skip(f"Snapshot missing required keys: {snapshot.keys()}")

        freq0 = int(snapshot["frequency"])
        mode0 = snapshot["mode"]
        power0 = int(snapshot["power"])

        if not isinstance(mode0, Mode):
            pytest.skip(f"Unexpected snapshot mode type: {type(mode0).__name__}")

        try:
            await radio.set_frequency(freq0 + 1000)
            await radio.set_mode(Mode.CW, filter_width=1)
            await radio.set_power(max(1, min(255, power0 - 5)))
            await asyncio.sleep(0.15)
        finally:
            await radio.restore_state(snapshot)

        # Validate restore of core keys.
        freq1 = await radio.get_frequency()
        mode1, _ = await radio.get_mode()
        power1 = await radio.get_power()

        assert freq1 == freq0, f"Frequency restore failed: {freq0} != {freq1}"
        assert mode1 == mode0.name, f"Mode restore failed: {mode0.name} != {mode1}"

        # Some rigs quantize power; tolerate tiny drift.
        assert abs(power1 - power0) <= 2, f"Power restore failed: {power0} vs {power1}"

        # Optional verification if filter exists in snapshot.
        filt0 = snapshot.get("filter")
        if isinstance(filt0, int):
            _, filt1 = await radio.get_mode_info()
            assert filt1 == filt0

        print("snapshot_state/restore_state roundtrip ✓")
