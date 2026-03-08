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

export function clearFinishedCommands() {
  commands = commands.filter((c) => c.status === 'pending');
}
