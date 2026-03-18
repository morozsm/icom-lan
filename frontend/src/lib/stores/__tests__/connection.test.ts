import { describe, it, expect, beforeEach, vi } from 'vitest';

describe('connection store', () => {
  let store: typeof import('../connection.svelte');

  beforeEach(async () => {
    vi.resetModules();
    store = await import('../connection.svelte');
  });

  it('starts disconnected', () => {
    expect(store.getConnectionStatus()).toBe('disconnected');
    expect(store.isConnected()).toBe(false);
  });

  it('partial when only http connected', () => {
    store.setHttpConnected(true);
    expect(store.getConnectionStatus()).toBe('partial');
    expect(store.isConnected()).toBe(false);
  });

  it('partial when only ws connected', () => {
    store.setWsConnected(true);
    expect(store.getConnectionStatus()).toBe('partial');
    expect(store.isConnected()).toBe(false);
  });

  it('connected when both http and ws connected', () => {
    store.setHttpConnected(true);
    store.setWsConnected(true);
    expect(store.getConnectionStatus()).toBe('connected');
    expect(store.isConnected()).toBe(true);
  });

  it('disconnected when both http and ws disconnected', () => {
    store.setHttpConnected(true);
    store.setWsConnected(true);
    store.setHttpConnected(false);
    store.setWsConnected(false);
    expect(store.getConnectionStatus()).toBe('disconnected');
    expect(store.isConnected()).toBe(false);
  });

  it('setLastResponseTime stores the value', () => {
    store.setLastResponseTime(1234567890);
    expect(store.getLastResponseTime()).toBe(1234567890);
  });

  it('lastResponseTime starts null', () => {
    expect(store.getLastResponseTime()).toBeNull();
  });

  it('getHttpConnected and getWsConnected reflect their state', () => {
    store.setHttpConnected(true);
    expect(store.getHttpConnected()).toBe(true);
    expect(store.getWsConnected()).toBe(false);
  });

  it('tracks reconnecting flag explicitly', () => {
    store.setReconnecting(true);
    expect(store.isReconnecting()).toBe(true);
    store.setReconnecting(false);
    expect(store.isReconnecting()).toBe(false);
  });

  it('markStateUpdated clears stale state', () => {
    store.markStateUpdated();
    expect(store.isStale()).toBe(false);
  });
});
