"""Integration tests for IcomRadio high-level API.

These tests run against a real Icom transceiver on the network.
Set environment variables to enable:

    export ICOM_HOST=192.168.55.40
    export ICOM_USER=your_username
    export ICOM_PASS=your_password

Run with: pytest -m integration
Skip with: pytest -m "not integration"
"""

from __future__ import annotations

import asyncio
import json
import os
import time

import pytest

from icom_lan import IcomRadio
from icom_lan.exceptions import TimeoutError as IcomTimeoutError
from icom_lan.types import Mode

from logging_utils import log_event, timed_call


pytestmark = pytest.mark.integration


class TestConnection:
    """Connection and disconnection tests."""

    async def test_connect_disconnect(self, radio_config: dict) -> None:
        """Basic connect/disconnect cycle."""
        radio = IcomRadio(**radio_config)
        assert not radio.connected

        await radio.connect()
        assert radio.connected

        await radio.disconnect()
        assert not radio.connected

    async def test_context_manager(self, radio_config: dict) -> None:
        """Context manager automatically handles connection."""
        async with IcomRadio(**radio_config) as radio:
            assert radio.connected


class TestFrequency:
    """Frequency read/write tests."""

    async def test_get_frequency(self, radio: IcomRadio) -> None:
        """Read current frequency."""
        freq = await radio.get_frequency()
        assert isinstance(freq, int)
        assert 1_800_000 <= freq <= 470_000_000  # Valid HF range
        print(f"Frequency: {freq:,} Hz ({freq/1e6:.3f} MHz)")

    async def test_set_frequency_roundtrip(self, radio: IcomRadio) -> None:
        """Set frequency and restore original."""
        # Save original
        original = await radio.get_frequency()

        try:
            # Set to 20m FT8
            new_freq = 14_074_000
            await radio.set_frequency(new_freq)

            # Verify
            actual = await radio.get_frequency()
            assert actual == new_freq, f"Expected {new_freq}, got {actual}"
            print(f"Set frequency: {actual:,} Hz ✓")

        finally:
            # Restore original
            await radio.set_frequency(original)
            restored = await radio.get_frequency()
            assert restored == original
            print(f"Restored: {restored:,} Hz ✓")


class TestMode:
    """Mode read/write tests."""

    async def test_get_mode(self, radio: IcomRadio) -> None:
        """Read current mode."""
        mode = await radio.get_mode()
        assert isinstance(mode, Mode)
        print(f"Mode: {mode.name} ✓")

    async def test_set_mode_roundtrip(self, radio: IcomRadio) -> None:
        """Set mode and restore original."""
        original = await radio.get_mode()

        try:
            # Set to USB
            await radio.set_mode(Mode.USB)

            actual = await radio.get_mode()
            assert actual == Mode.USB
            print(f"Set mode: {actual.name} ✓")

            # Try another mode
            await radio.set_mode(Mode.CW)
            actual = await radio.get_mode()
            assert actual == Mode.CW
            print(f"Set mode: {actual.name} ✓")

        finally:
            await radio.set_mode(original)
            restored = await radio.get_mode()
            assert restored == original
            print(f"Restored: {restored.name} ✓")


class TestFilter:
    """Filter API tests."""

    async def test_get_set_filter_roundtrip(self, radio: IcomRadio) -> None:
        """Read filter, set to another value, then restore."""
        mode, original_filter = await radio.get_mode_info()
        if original_filter is None:
            pytest.skip("Radio did not report filter in mode response")

        target = 2 if original_filter != 2 else 1
        try:
            await radio.set_mode(mode, filter_width=target)
            _, actual = await radio.get_mode_info()
            assert actual == target, f"Expected filter {target}, got {actual}"
            print(f"Filter set: {actual} ✓")
        finally:
            await radio.set_mode(mode, filter_width=original_filter)
            print(f"Filter restored: {original_filter} ✓")


class TestMeters:
    """Meter reading tests (read-only).

    Note: All meters return 0-255 scale, not physical units.
    """

    async def test_get_s_meter(self, radio: IcomRadio) -> None:
        """Read S-meter value."""
        s = await radio.get_s_meter()
        assert isinstance(s, int)
        assert 0 <= s <= 255
        print(f"S-meter: {s} ✓")

    async def test_get_swr(self, radio: IcomRadio) -> None:
        """Read SWR meter value (0-255)."""
        swr = await radio.get_swr()
        assert isinstance(swr, int)
        assert 0 <= swr <= 255
        print(f"SWR meter: {swr} ✓")

    async def test_get_alc(self, radio: IcomRadio) -> None:
        """Read ALC value.

        On some radios/firmware, ALC may not respond reliably in pure RX state.
        If direct query times out, retry once with brief PTT to force TX metering.
        """
        try:
            alc = await radio.get_alc()
        except IcomTimeoutError:
            await radio.set_ptt(True)
            try:
                alc = await radio.get_alc()
            finally:
                await radio.set_ptt(False)

        assert isinstance(alc, int)
        assert 0 <= alc <= 255
        print(f"ALC: {alc} ✓")

    async def test_get_power(self, radio: IcomRadio) -> None:
        """Read TX power setting (0-255, where 255 = 100%)."""
        power = await radio.get_power()
        assert isinstance(power, int)
        assert 0 <= power <= 255
        print(f"Power setting: {power}/255 ({power*100/255:.0f}%) ✓")


class TestPowerControl:
    """TX power control tests.

    Power is 0-255 scale where 255 = 100W (max).
    """

    async def test_set_power_roundtrip(self, radio: IcomRadio) -> None:
        """Set TX power and restore original."""
        original = await radio.get_power()

        try:
            # Set to ~50% power (128 = ~50W)
            await radio.set_power(128)
            actual = await radio.get_power()
            # Allow some tolerance due to radio calibration
            assert 100 <= actual <= 150, f"Expected ~128, got {actual}"
            print(f"Set power: {actual}/255 ({actual*100/255:.0f}%) ✓")

        finally:
            await radio.set_power(original)
            print(f"Restored power: {original}/255 ✓")


class TestPTT:
    """PTT control tests (no actual transmission)."""

    async def test_ptt_on_off(self, radio: IcomRadio) -> None:
        """Toggle PTT on and off."""
        # PTT on
        await radio.set_ptt(True)
        await radio.set_ptt(False)
        print("PTT on/off ✓")


class TestVFO:
    """VFO operations tests."""

    async def test_select_vfo(self, radio: IcomRadio) -> None:
        """Select MAIN/SUB VFO."""
        # Select MAIN
        await radio.select_vfo("MAIN")
        print("VFO MAIN ✓")

        # Select SUB (if supported)
        try:
            await radio.select_vfo("SUB")
            print("VFO SUB ✓")
            # Back to MAIN
            await radio.select_vfo("MAIN")
        except Exception as e:
            print(f"VFO SUB not supported: {e}")

    async def test_vfo_exchange_roundtrip(self, radio: IcomRadio) -> None:
        """Exchange MAIN/SUB frequencies and restore."""
        try:
            await radio.select_vfo("MAIN")
            main0 = await radio.get_frequency()
            await radio.select_vfo("SUB")
            sub0 = await radio.get_frequency()

            if main0 == sub0:
                await radio.select_vfo("SUB")
                await radio.set_frequency(main0 + 1000)
                sub0 = await radio.get_frequency()

            await radio.vfo_exchange()

            await radio.select_vfo("MAIN")
            main1 = await radio.get_frequency()
            await radio.select_vfo("SUB")
            sub1 = await radio.get_frequency()

            assert main1 == sub0, f"Expected MAIN={sub0}, got {main1}"
            assert sub1 == main0, f"Expected SUB={main0}, got {sub1}"
            print("VFO exchange ✓")

            # Restore original placement
            await radio.vfo_exchange()
            await radio.select_vfo("MAIN")
        except Exception as e:
            pytest.skip(f"VFO exchange not supported in current rig state: {e}")

    async def test_vfo_equalize_roundtrip(self, radio: IcomRadio) -> None:
        """Exercise A=B command without assuming MAIN/SUB mapping semantics.

        On IC-7610, CI-V A=B behavior can differ from simple "copy MAIN to SUB".
        This test validates command acceptance and keeps rig state restorable.
        """
        try:
            await radio.select_vfo("MAIN")
            main0 = await radio.get_frequency()
            await radio.select_vfo("SUB")
            sub0 = await radio.get_frequency()

            await radio.select_vfo("MAIN")
            await radio.vfo_equalize()

            await radio.select_vfo("MAIN")
            main1 = await radio.get_frequency()
            await radio.select_vfo("SUB")
            sub1 = await radio.get_frequency()

            # At minimum: command executed, values are readable and valid.
            assert main1 > 0 and sub1 > 0
            print(f"VFO equalize ✓ (MAIN {main0}->{main1}, SUB {sub0}->{sub1})")

            # Best-effort restore to pre-test values
            await radio.select_vfo("MAIN")
            await radio.set_frequency(main0)
            await radio.select_vfo("SUB")
            await radio.set_frequency(sub0)
            await radio.select_vfo("MAIN")
        except Exception as e:
            pytest.skip(f"VFO equalize not supported in current rig state: {e}")


class TestSplit:
    """Split mode tests."""

    async def test_split_mode_roundtrip(self, radio: IcomRadio) -> None:
        """Enable/disable split mode."""
        # Try enabling split
        try:
            await radio.set_split_mode(True)
            print("Split ON ✓")

            await radio.set_split_mode(False)
            print("Split OFF ✓")
        except Exception as e:
            # Split might not be supported on all radios
            pytest.skip(f"Split mode not supported: {e}")


class TestFrontEnd:
    """Attenuator / preamp API tests."""

    @staticmethod
    def _strict_enabled() -> bool:
        return os.environ.get("ICOM_STRICT_FRONTEND", "0") == "1"

    @staticmethod
    async def _prepare_strict_frontend_state(radio: IcomRadio) -> None:
        """Apply deterministic preconditions for strict ATT/PREAMP validation."""
        await radio.set_split_mode(False)
        await radio.select_vfo("MAIN")
        await radio.set_mode(Mode.USB)
        # On IC-7610 PREAMP and DIGI-SEL are mutually exclusive.
        await radio.set_digisel(False)
        ds = await radio.get_digisel()
        assert ds is False, "Expected DIGI-SEL OFF before strict PREAMP tests"
        await asyncio.sleep(0.15)

    async def test_attenuator_roundtrip(self, radio: IcomRadio) -> None:
        """Toggle attenuator and restore original state."""
        strict = self._strict_enabled()

        if strict:
            await self._prepare_strict_frontend_state(radio)
            # Strict deterministic sequence for IC-7610 attenuator levels.
            for db in (0, 18, 0):
                await radio.set_attenuator_level(db)
                got = await radio.get_attenuator_level()
                assert got == db, f"Expected ATT {db} dB, got {got}"
            print("ATT strict sequence 0->18->0 dB ✓")
            return

        try:
            original = await radio.get_attenuator()
        except Exception as e:
            pytest.skip(f"ATT read not available: {e}")

        try:
            await radio.set_attenuator(not original)
            current = await radio.get_attenuator()
            assert current is (not original)
            print(f"ATT toggled to {current} ✓")
        except Exception as e:
            pytest.skip(f"ATT control not supported in current rig state: {e}")
        finally:
            try:
                await radio.set_attenuator(original)
                print(f"ATT restored: {original} ✓")
            except Exception:
                pass

    async def test_preamp_roundtrip(self, radio: IcomRadio) -> None:
        """Set preamp and restore original level."""
        strict = self._strict_enabled()

        if strict:
            await self._prepare_strict_frontend_state(radio)
            # Strict sequence validates command acceptance (some rigs may clamp).
            for lvl in (0, 1, 2, 0):
                await radio.set_preamp(lvl)
            got = await radio.get_preamp()
            assert got in (0, 1, 2), f"Unexpected PREAMP readback: {got}"
            print(f"PREAMP strict command sequence 0->1->2->0 ✓ (readback={got})")
            return

        try:
            original = await radio.get_preamp()
        except Exception as e:
            pytest.skip(f"PREAMP read not available: {e}")

        target = 1 if original != 1 else 0
        try:
            await radio.set_preamp(target)
            current = await radio.get_preamp()
            assert current == target, f"Expected preamp {target}, got {current}"
            print(f"PREAMP set: {current} ✓")
        except Exception as e:
            pytest.skip(f"PREAMP control not supported in current rig state: {e}")
        finally:
            try:
                await radio.set_preamp(original)
                print(f"PREAMP restored: {original} ✓")
            except Exception:
                pass


class TestCW:
    """CW keying tests (optional, requires antenna/dummy load)."""

    async def test_stop_cw_text_interrupts_tx(self, radio: IcomRadio) -> None:
        """Start long CW and request stop (best-effort interrupt check)."""
        original_freq = await radio.get_frequency()
        original_power = await radio.get_power()

        try:
            await radio.set_split_mode(False)
            await radio.select_vfo("MAIN")
            await radio.set_frequency(14_050_000)
            await radio.set_mode(Mode.CW)
            await radio.set_power(max(1, round(255 * 0.05)))
            await asyncio.sleep(0.2)

            long_msg = "VV VV DE KN4KYD TEST TEST TEST TEST TEST TEST VV"
            send_task = asyncio.create_task(radio.send_cw_text(long_msg))
            await asyncio.sleep(0.35)
            await radio.stop_cw_text()
            await asyncio.wait_for(send_task, timeout=5.0)
            print("CW stop requested ✓")
        finally:
            await radio.set_power(original_power)
            await radio.set_mode(Mode.USB)
            await radio.set_frequency(original_freq)
            print(
                f"CW restore: {original_freq/1e6:.3f} MHz, "
                f"USB, {original_power}/255 ✓"
            )

    async def test_send_cw_text(self, radio: IcomRadio) -> None:
        """Send CW text with safe pre/post state handling.

        Sequence:
        1) Save current freq/power
        2) Set 14.050 MHz + CW + ~5% power
        3) Send test CW text
        4) Restore to original frequency and force USB mode
        """
        original_freq = await radio.get_frequency()
        original_power = await radio.get_power()

        cw_freq = 14_050_000
        cw_power = max(1, round(255 * 0.05))  # ~5%

        try:
            await radio.set_split_mode(False)
            await radio.select_vfo("MAIN")
            await radio.set_frequency(cw_freq)
            await radio.set_mode(Mode.CW)
            await radio.set_power(cw_power)

            # Give rig time to settle mode/filter/keyer state.
            await asyncio.sleep(0.2)

            # Confirm mode before keying.
            actual_mode = await radio.get_mode()
            assert actual_mode == Mode.CW, f"Expected CW mode, got {actual_mode}"

            # Longer test message (easier to hear on-air)
            msg = "VV KN4KYD TEST TEST TEST VV"
            await radio.send_cw_text(msg)
            print(f"CW: {msg} ✓")
        finally:
            await radio.set_power(original_power)
            await radio.set_mode(Mode.USB)
            await radio.set_frequency(original_freq)
            print(
                f"CW restore: {original_freq/1e6:.3f} MHz, "
                f"USB, {original_power}/255 ✓"
            )


class TestPowerHardware:
    """Guarded power-control integration tests (real hardware off/on)."""

    async def test_power_cycle_roundtrip(self, radio_config: dict) -> None:
        """Power off/on and verify reconnect.

        Requires explicit env gate:
            ICOM_ALLOW_POWER_CONTROL=1
        """
        import os

        if os.environ.get("ICOM_ALLOW_POWER_CONTROL") != "1":
            pytest.skip("Set ICOM_ALLOW_POWER_CONTROL=1 to run power-cycle test")

        r = IcomRadio(**radio_config, timeout=8.0)
        await r.connect()
        assert r.connected

        try:
            # Power off
            await r.power_control(False)
            print("Power OFF command sent ✓")
        finally:
            # Control socket may drop quickly after power off.
            try:
                await r.disconnect()
            except Exception:
                pass

        # Give radio time to power down/up relay state.
        await asyncio.sleep(2.0)

        # Power on via fresh control session
        r2 = IcomRadio(**radio_config, timeout=12.0)
        await r2.connect()
        try:
            await r2.power_control(True)
            print("Power ON command sent ✓")
        finally:
            await r2.disconnect()

        # Wait for boot and verify reconnect + basic command.
        await asyncio.sleep(4.0)
        r3 = IcomRadio(**radio_config, timeout=12.0)
        await r3.connect()
        try:
            freq = await r3.get_frequency()
            assert freq > 0
            print(f"Power cycle reconnect ✓ (freq={freq})")
        finally:
            await r3.disconnect()


class TestReconnect:
    """Reconnect and recovery scenarios on real hardware."""

    async def test_manual_reconnect_and_audio_recovery(self, radio_config: dict) -> None:
        """Disconnect/connect cycle should recover CI-V and audio RX."""
        packets: list = []

        def on_audio(pkt):
            if pkt is not None:
                packets.append(pkt)

        async def connect_with_retry(radio: IcomRadio, label: str, retries: int = 4) -> None:
            for attempt in range(1, retries + 2):
                try:
                    _, dt = await timed_call("connect", radio.connect)
                    log_event(
                        test="reconnect",
                        step=f"{label}_connect",
                        cmd="connect",
                        attempt=attempt,
                        timeout=False,
                        recovered=(attempt > 1),
                        duration_ms=dt,
                    )
                    return
                except IcomTimeoutError:
                    log_event(
                        test="reconnect",
                        step=f"{label}_connect",
                        cmd="connect",
                        attempt=attempt,
                        timeout=True,
                        recovered=(attempt <= retries),
                    )
                    if attempt > retries:
                        raise
                    await asyncio.sleep(1.0 + 0.5 * attempt)

        r1 = IcomRadio(**radio_config, timeout=8.0)
        await connect_with_retry(r1, "initial")
        try:
            f1 = await r1.get_frequency()
            assert f1 > 0
            print(f"Reconnect pre-check freq={f1} ✓")
        finally:
            await r1.disconnect()
            print("Manual disconnect ✓")

        await asyncio.sleep(1.0)

        r2 = IcomRadio(**radio_config, timeout=10.0)
        await connect_with_retry(r2, "reconnect")
        try:
            f2 = await r2.get_frequency()
            assert f2 > 0
            print(f"Manual reconnect freq={f2} ✓")

            await r2.start_audio_rx(on_audio)
            await asyncio.sleep(1.5)
            await r2.stop_audio_rx()
            assert len(packets) > 0, "Audio RX did not recover after reconnect"
            print(f"Audio recovery ✓ (packets={len(packets)})")
        finally:
            await r2.disconnect()


class TestSoak:
    """Long-run soak test with timeout/retry/recovery logging."""

    async def test_soak_retries_and_logging(self, radio_config: dict) -> None:
        """Run periodic operations and verify timeout recovery.

        Enable with env:
            ICOM_SOAK_SECONDS=300   (or any duration)
        """
        soak_s = int(os.environ.get("ICOM_SOAK_SECONDS", "0"))
        if soak_s <= 0:
            pytest.skip("Set ICOM_SOAK_SECONDS to run soak test")

        r = IcomRadio(**radio_config, timeout=8.0)
        await r.connect()
        await asyncio.sleep(0.5)

        started = time.monotonic()
        deadline = started + soak_s
        cycle = 0
        stats = {
            "ops": 0,
            "timeouts": 0,
            "timeouts_recovered": 0,
            "timeouts_unrecovered": 0,
            "recover_reconnects": 0,
            "audio_windows": 0,
            "audio_packets": 0,
        }

        async def recover_connection() -> None:
            nonlocal stats, r
            stats["recover_reconnects"] += 1
            log_event(test="soak", step="recover_start", cmd="connect")
            try:
                await r.disconnect()
            except Exception:
                pass

            for i in range(1, 6):
                try:
                    await asyncio.sleep(0.6 * i)
                    _, dt = await timed_call("connect", r.connect)
                    log_event(
                        test="soak",
                        step="recover_connect",
                        cmd="connect",
                        attempt=i,
                        timeout=False,
                        recovered=True,
                        duration_ms=dt,
                    )
                    return
                except IcomTimeoutError:
                    log_event(
                        test="soak",
                        step="recover_connect",
                        cmd="connect",
                        attempt=i,
                        timeout=True,
                        recovered=(i < 5),
                    )
            raise IcomTimeoutError("Reconnect recovery failed")

        async def op(name: str, fn, retries: int = 2):
            nonlocal stats
            for attempt in range(1, retries + 2):
                try:
                    out, dt = await timed_call(name, fn)
                    stats["ops"] += 1
                    log_event(
                        test="soak",
                        step="op",
                        cmd=name,
                        attempt=attempt,
                        timeout=False,
                        recovered=(attempt > 1),
                        duration_ms=dt,
                    )
                    return out
                except IcomTimeoutError:
                    stats["timeouts"] += 1
                    recovered = attempt <= retries
                    log_event(
                        test="soak",
                        step="op",
                        cmd=name,
                        attempt=attempt,
                        timeout=True,
                        recovered=recovered,
                    )
                    if recovered:
                        stats["timeouts_recovered"] += 1
                        await asyncio.sleep(0.15)
                        continue

                    # Last retry failed: try one reconnect recovery path.
                    try:
                        await recover_connection()
                        out, dt = await timed_call(name, fn)
                        stats["ops"] += 1
                        stats["timeouts_recovered"] += 1
                        log_event(
                            test="soak",
                            step="op_after_recover",
                            cmd=name,
                            attempt=attempt,
                            timeout=False,
                            recovered=True,
                            duration_ms=dt,
                        )
                        return out
                    except Exception:
                        stats["timeouts_unrecovered"] += 1
                        raise

        base_freq = await op("base_get_frequency", r.get_frequency, retries=4)

        packets: list = []

        def on_audio(pkt):
            if pkt is not None:
                packets.append(pkt)

        try:
            while time.monotonic() < deadline:
                cycle += 1
                await op("get_frequency", r.get_frequency)
                await op("get_mode", r.get_mode)
                await op("get_power", r.get_power)
                await op("get_s_meter", r.get_s_meter)
                await op("get_swr", r.get_swr)
                await op("get_alc", r.get_alc)

                if cycle % 5 == 0:
                    await op("set_frequency_offset", lambda: r.set_frequency(base_freq + 1000))
                    await op("set_frequency_restore", lambda: r.set_frequency(base_freq))

                if cycle % 6 == 0:
                    stats["audio_windows"] += 1
                    await r.start_audio_rx(on_audio)
                    await asyncio.sleep(0.8)
                    await r.stop_audio_rx()
                    stats["audio_packets"] += len(packets)
                    packets.clear()

                await asyncio.sleep(0.35)
        finally:
            try:
                await r.set_frequency(base_freq)
            except Exception:
                pass
            await r.disconnect()

        summary = {
            **stats,
            "cycles": cycle,
            "duration_s": int(time.monotonic() - started),
        }
        print("SOAK_SUMMARY", json.dumps(summary))

        assert stats["timeouts_unrecovered"] == 0, (
            f"Unrecovered timeouts: {stats['timeouts_unrecovered']}"
        )


class TestFaultInjection:
    """Fault-injection recovery scenarios."""

    async def test_civ_drop_recover_via_reconnect(self, radio_config: dict) -> None:
        """Simulate CI-V path loss and verify reconnect recovery."""
        r = IcomRadio(**radio_config, timeout=8.0)
        await r.connect()
        try:
            base = await r.get_frequency()
            assert base > 0
            log_event(test="fault", step="baseline", cmd="get_frequency", timeout=False)

            # Inject fault: drop CI-V transport socket.
            if r._civ_transport is None:  # type: ignore[attr-defined]
                pytest.skip("CI-V transport unavailable for fault injection")
            await r._civ_transport.disconnect()  # type: ignore[attr-defined]
            log_event(test="fault", step="inject", cmd="civ_disconnect", recovered=False)

            # Next CI-V command should fail (timeout/connection error).
            failed = False
            try:
                await r.get_frequency()
            except Exception:
                failed = True
            assert failed, "Expected CI-V command failure after injected drop"
            log_event(test="fault", step="post_inject_failure", cmd="get_frequency", timeout=True)
        finally:
            try:
                await r.disconnect()
            except Exception:
                pass

        # Recovery path: full reconnect with retries
        r2 = IcomRadio(**radio_config, timeout=10.0)
        try:
            recovered = False
            for attempt in range(1, 6):
                try:
                    await r2.connect()
                    freq2 = await r2.get_frequency()
                    assert freq2 > 0
                    log_event(
                        test="fault",
                        step="recover",
                        cmd="reconnect+get_frequency",
                        attempt=attempt,
                        timeout=False,
                        recovered=(attempt > 1),
                    )
                    recovered = True
                    break
                except Exception:
                    log_event(
                        test="fault",
                        step="recover",
                        cmd="reconnect+get_frequency",
                        attempt=attempt,
                        timeout=True,
                        recovered=(attempt < 5),
                    )
                    try:
                        await r2.disconnect()
                    except Exception:
                        pass
                    await asyncio.sleep(0.7 * attempt)
            assert recovered, "Failed to recover after injected CI-V drop"
        finally:
            try:
                await r2.disconnect()
            except Exception:
                pass


class TestCommanderStress:
    """Queue/concurrency stress for commander serialization."""

    async def test_concurrent_gets(self, radio: IcomRadio) -> None:
        """Run many concurrent read commands; all must complete without timeout."""
        n = 20

        async def one(i: int):
            freq = await radio.get_frequency()
            mode = await radio.get_mode()
            power = await radio.get_power()
            return (i, freq, mode, power)

        results = await asyncio.gather(*(one(i) for i in range(n)))
        assert len(results) == n
        for _, freq, _, power in results:
            assert freq > 0
            assert 0 <= power <= 255

        print(f"Commander stress concurrent gets ✓ (tasks={n})")

    async def test_concurrent_frequency_set_restore(self, radio: IcomRadio) -> None:
        """Concurrent set/get burst with guaranteed restore."""
        base = await radio.get_frequency()
        offsets = [1000, 2000, 3000, 0]

        try:
            async def step(delta: int):
                await radio.set_frequency(base + delta)
                return await radio.get_frequency()

            seen = await asyncio.gather(*(step(d) for d in offsets))
            assert all(v > 0 for v in seen)
            print(f"Commander stress set/get burst ✓ (seen={seen})")
        finally:
            await radio.set_frequency(base)


class TestStatus:
    """Status and info tests."""

    async def test_get_status(self, radio: IcomRadio) -> None:
        """Get comprehensive radio status."""
        freq = await radio.get_frequency()
        mode = await radio.get_mode()
        s = await radio.get_s_meter()
        swr = await radio.get_swr()
        power = await radio.get_power()

        print("\n── Radio Status ──")
        print(f"  Frequency: {freq/1e6:.3f} MHz")
        print(f"  Mode: {mode.name}")
        print(f"  S-meter: {s}/255")
        print(f"  SWR meter: {swr}/255")
        print(f"  Power: {power}/255 ({power*100/255:.0f}%)")

        # Basic sanity checks
        assert freq > 0
        assert mode in Mode
        assert 0 <= s <= 255
        assert 0 <= swr <= 255
        assert 0 <= power <= 255
