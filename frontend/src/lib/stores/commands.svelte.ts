import type { PendingCommand } from '../types/state';

// Command queue — commands awaiting server acknowledgment
let commands = $state<PendingCommand[]>([]);

export function getCommands() {
  return commands;
}

export function addCommand(cmd: PendingCommand) {
  commands.push(cmd);
}

export function ackCommand(id: string) {
  const cmd = commands.find((c) => c.id === id);
  if (cmd) cmd.status = 'acked';
}

export function failCommand(id: string) {
  const cmd = commands.find((c) => c.id === id);
  if (cmd) cmd.status = 'failed';
}

/**
 * Remove all finished commands (both `acked` and `failed`) from the queue.
 * Only `pending` commands are kept. Call this after processing acknowledged
 * results to prevent unbounded queue growth. If you need to inspect or retry
 * failed commands, do so before calling this function.
 */
export function clearFinishedCommands() {
  commands = commands.filter((c) => c.status === 'pending');
}
