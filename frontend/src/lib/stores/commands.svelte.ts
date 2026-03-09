import type { PendingCommand } from '../types/state';
import { makeCommandId } from '../types/protocol';

// Command queue — commands awaiting server acknowledgment
let commands = $state<PendingCommand[]>([]);

let hasPendingDerived = $derived(commands.some((c) => c.status === 'pending'));

export function getPendingCommands(): PendingCommand[] {
  return commands;
}

export function addCommand(type: string, payload: unknown): PendingCommand {
  const cmd: PendingCommand = {
    id: makeCommandId(),
    type,
    payload,
    createdAt: Date.now(),
    status: 'pending',
    timeoutMs: 5000,
  };
  commands.push(cmd);
  setTimeout(() => {
    const current = commands.find((c) => c.id === cmd.id);
    if (current?.status === 'pending') {
      current.status = 'failed';
    }
  }, cmd.timeoutMs);
  return cmd;
}

export function ackCommand(id: string): void {
  const cmd = commands.find((c) => c.id === id);
  if (cmd) cmd.status = 'acked';
}

export function failCommand(id: string): void {
  const cmd = commands.find((c) => c.id === id);
  if (cmd) cmd.status = 'failed';
}

/**
 * Remove all finished commands (both `acked` and `failed`) from the queue.
 * Only `pending` commands are kept. Call this after processing acknowledged
 * results to prevent unbounded queue growth. If you need to inspect or retry
 * failed commands, do so before calling this function.
 */
export function clearFinishedCommands(): void {
  commands = commands.filter((c) => c.status === 'pending');
}

export function hasPending(): boolean {
  return hasPendingDerived;
}
