/**
 * VFO adapter — derives VFO view-model props from runtime state.
 *
 * Call inside a $derived() block for reactivity.
 */

import { runtime } from '../frontend-runtime';
import { toVfoProps, toVfoOpsProps } from '../props/panel-props';
import type { VfoStateProps, VfoOpsProps } from '../props/panel-props';

export function deriveMainVfo(): VfoStateProps {
  return toVfoProps(runtime.state, 'main');
}

export function deriveSubVfo(): VfoStateProps {
  return toVfoProps(runtime.state, 'sub');
}

export function deriveVfoOps(): VfoOpsProps {
  return toVfoOpsProps(runtime.state, runtime.caps);
}
