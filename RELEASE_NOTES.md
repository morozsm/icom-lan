# icom-lan 0.16.2

**Release date:** April 15, 2026

## Highlights

The web UI Connect/Disconnect button has been completely reworked to control
the full frontend lifecycle — all WebSocket channels, HTTP polling, audio,
and MediaSession are cleanly torn down on Disconnect and restored on Connect,
without affecting the server's connection to the radio. Companion tuning step
sync with the RC-28 dispatcher has also been added.

## What's New

### Companion Tuning Step Sync
- Tuning step is synced to the RC-28 companion dispatcher
- Incoming `companion_state` WS messages update the step in real time
- Auto-step preference is preserved when syncing from companion

### Connect/Disconnect Lifecycle
- Disconnect shuts down all browser-side connections: audio (RX/TX),
  all WebSocket channels (control + scope), HTTP state polling, and
  MediaSession silent audio loop
- Connect restores everything — including named scope/audio channels
- Server-to-radio connection is never affected; other clients keep working
- StatusBar button now tracks WebSocket connection state for immediate feedback

### Transport
- Suppressed misleading `_packet_pump` warning on disconnect
- Reduced UDP error log verbosity

## Breaking Changes

None.

## Install / Upgrade

```bash
pip install icom-lan==0.16.2
# or upgrade:
pip install --upgrade icom-lan
```

## Commits

```
ebee64b fix: use setTuningStepFromCompanion to preserve auto-step preference
0da9a17 feat: handle companion_state WS messages for tuning step sync
9e858b5 fix: reconnect all WS channels (scope, audio) after connect
40e8983 fix: Connect/Disconnect now controls full frontend lifecycle
1f3e18a feat: sync tuning step to companion RC-28 dispatcher
76a158d fix: StatusBar connect button tracks WebSocket state, not radio status
ecc1704 fix: web Connect/Disconnect now controls only WebSocket, not radio connection
31d9c9a fix: suppress misleading transport warning and reduce UDP error noise
```
