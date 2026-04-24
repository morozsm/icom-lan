/**
 * Shared pending-focus cache — bridges the gap between a MAIN/SUB mode
 * badge click (which toggles `active` + `set_vfo`) and a subsequent mode
 * change that must target the just-focused receiver.  `activeReceiverParam()`
 * can lag during rapid clicks; see issue #720.
 *
 * Extracted from `components-v2/wiring/command-bus.ts` and
 * `lib/runtime/commands/panel-commands.ts` so both share a single state
 * instance (prerequisite for #1002).  See issue #1044.
 */

const PENDING_FOCUS_TTL_MS = 300;
let pendingFocusVfo: 'MAIN' | 'SUB' | null = null;
let pendingFocusAt = 0;

export function setPendingFocus(vfo: 'MAIN' | 'SUB'): void {
  pendingFocusVfo = vfo;
  pendingFocusAt = Date.now();
}

export function consumePendingFocus(): 'MAIN' | 'SUB' | null {
  if (pendingFocusVfo === null) return null;
  const fresh = Date.now() - pendingFocusAt < PENDING_FOCUS_TTL_MS;
  const vfo = pendingFocusVfo;
  pendingFocusVfo = null;
  pendingFocusAt = 0;
  return fresh ? vfo : null;
}
