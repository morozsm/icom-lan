/**
 * Audio adapter — derives RX audio view-model props from runtime state.
 *
 * Call deriveRxAudioProps() inside a $derived() block for reactivity.
 * getRxAudioHandlers() returns stable callbacks — safe to call once.
 */

import { runtime } from '../frontend-runtime';
import { toRxAudioProps, type RxAudioProps } from '../props/panel-props';
import { makeRxAudioHandlers } from '../commands/panel-commands';

export function deriveRxAudioProps(): RxAudioProps {
  const state = runtime.state;
  const caps = runtime.caps;
  const audio = runtime.audio;
  return toRxAudioProps(state, caps, audio);
}

// Stable handler object — delegates to existing command-bus logic.
// Created once; safe to call at module scope.
const _handlers = makeRxAudioHandlers();

export function getRxAudioHandlers() {
  return _handlers;
}
