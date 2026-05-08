"""Safe audio capability probe runner helpers."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable, Mapping

from rigplane.audio.probe import (
    AudioProbeArtifact,
    AudioProbeCandidate,
    AudioProbeResult,
    AudioProbeStatus,
    classify_stock_radio_lan_probe_error,
)

AudioProbeAttempt = Callable[[AudioProbeCandidate], Awaitable[AudioProbeResult]]


async def run_audio_probe(
    candidates: Iterable[AudioProbeCandidate],
    attempt: AudioProbeAttempt,
) -> list[AudioProbeResult]:
    """Run probe candidates sequentially and normalize attempt failures."""

    results: list[AudioProbeResult] = []
    for candidate in candidates:
        try:
            results.append(await attempt(candidate))
        except Exception as exc:
            status, reason = classify_stock_radio_lan_probe_error(exc)
            results.append(
                AudioProbeResult(
                    candidate=candidate,
                    status=status,
                    phase="conninfo"
                    if status is AudioProbeStatus.REJECTED
                    else "runtime",
                    reason=reason,
                    error=str(exc),
                )
            )
    return results


def dry_run_probe_results(
    candidates: Iterable[AudioProbeCandidate],
) -> list[AudioProbeResult]:
    """Return skipped results for operators validating the probe plan."""

    return [
        AudioProbeResult(
            candidate=candidate,
            status=AudioProbeStatus.SKIPPED,
            phase="dry-run",
            reason="dry-run",
        )
        for candidate in candidates
    ]


def summarize_probe_results(
    results: Iterable[AudioProbeResult],
) -> dict[str, int]:
    """Count probe results by normalized status."""

    summary = {status.value: 0 for status in AudioProbeStatus}
    for result in results:
        summary[result.status.value] += 1
    return summary


def build_probe_artifact(
    *,
    model: str,
    profile_id: str,
    transport: str,
    results: list[AudioProbeResult],
    metadata: Mapping[str, object] | None = None,
) -> AudioProbeArtifact:
    """Build a machine-readable probe artifact with a stable summary."""

    merged_metadata: dict[str, object] = dict(metadata or {})
    merged_metadata["summary"] = summarize_probe_results(results)
    return AudioProbeArtifact(
        model=model,
        profile_id=profile_id,
        transport=transport,
        results=results,
        metadata=merged_metadata,
    )


__all__ = [
    "AudioProbeAttempt",
    "build_probe_artifact",
    "dry_run_probe_results",
    "run_audio_probe",
    "summarize_probe_results",
]
