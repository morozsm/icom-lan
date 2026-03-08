import { describe, it, expect, beforeEach, vi } from 'vitest';

describe('commands store', () => {
  let store: typeof import('../commands.svelte');

  beforeEach(async () => {
    vi.resetModules();
    store = await import('../commands.svelte');
  });

  it('starts empty', () => {
    expect(store.getPendingCommands()).toHaveLength(0);
    expect(store.hasPending()).toBe(false);
  });

  it('addCommand creates a command with correct shape', () => {
    const cmd = store.addCommand('set_freq', { freq: 14074000 });
    expect(cmd.type).toBe('set_freq');
    expect(cmd.payload).toEqual({ freq: 14074000 });
    expect(cmd.status).toBe('pending');
    expect(typeof cmd.id).toBe('string');
    expect(cmd.id.length).toBeGreaterThan(0);
    expect(cmd.createdAt).toBeGreaterThan(0);
    expect(cmd.timeoutMs).toBe(5000);
  });

  it('addCommand adds to queue', () => {
    store.addCommand('set_freq', {});
    store.addCommand('set_mode', {});
    expect(store.getPendingCommands()).toHaveLength(2);
  });

  it('hasPending is true when pending commands exist', () => {
    store.addCommand('set_freq', {});
    expect(store.hasPending()).toBe(true);
  });

  it('ackCommand transitions status to acked', () => {
    const cmd = store.addCommand('set_freq', {});
    store.ackCommand(cmd.id);
    const found = store.getPendingCommands().find((c) => c.id === cmd.id);
    expect(found?.status).toBe('acked');
  });

  it('failCommand transitions status to failed', () => {
    const cmd = store.addCommand('set_freq', {});
    store.failCommand(cmd.id);
    const found = store.getPendingCommands().find((c) => c.id === cmd.id);
    expect(found?.status).toBe('failed');
  });

  it('clearFinishedCommands removes acked and failed, keeps pending', () => {
    const a = store.addCommand('set_freq', {});
    const b = store.addCommand('set_mode', {});
    const c = store.addCommand('ptt_on', {});

    store.ackCommand(a.id);
    store.failCommand(b.id);
    // c stays pending

    store.clearFinishedCommands();
    const remaining = store.getPendingCommands();
    expect(remaining).toHaveLength(1);
    expect(remaining[0].id).toBe(c.id);
  });

  it('hasPending is false after all commands are cleared', () => {
    const cmd = store.addCommand('set_freq', {});
    store.ackCommand(cmd.id);
    store.clearFinishedCommands();
    expect(store.hasPending()).toBe(false);
  });

  it('ackCommand on unknown id is a no-op', () => {
    store.addCommand('set_freq', {});
    store.ackCommand('nonexistent-id');
    expect(store.getPendingCommands()[0].status).toBe('pending');
  });

  it('addCommand generates unique IDs', () => {
    const a = store.addCommand('set_freq', {});
    const b = store.addCommand('set_freq', {});
    expect(a.id).not.toBe(b.id);
  });
});
