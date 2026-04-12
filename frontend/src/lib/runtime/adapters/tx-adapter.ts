/**
 * TX adapter — provides audio TX lifecycle callbacks for PTT components.
 *
 * Replaces direct audioManager imports in TxPanel and MobileRadioLayout.
 */

import { runtime } from '../frontend-runtime';

export function getTxAudioControl() {
  return {
    startTx: () => runtime.startTx(),
    stopTx: () => runtime.stopTx(),
  };
}
