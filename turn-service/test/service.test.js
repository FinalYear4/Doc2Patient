import test from 'node:test';
import assert from 'node:assert/strict';
import { createTurnService } from '../src/service.js';

test('creates, activates, rotates, and monitors a TURN credential', async () => {
  const calls = { create: 0, ice: 0, usage: 0 };
  const metered = {
    async createCredential() {
      calls.create += 1;
      return { username: `user-${calls.create}`, apiKey: `api-${calls.create}`, label: 'test' };
    },
    async getIceServers(apiKey) {
      calls.ice += 1;
      return [{ urls: `turn:${apiKey}.example.test`, username: 'u', credential: 'p' }];
    },
    async getUsage() {
      calls.usage += 1;
      return { usageInGB: 1.25 };
    }
  };
  const state = { active: null, history: [] };
  const store = {
    async init() {},
    async getActive() { return state.active; },
    async activate(credential) { state.active = credential; state.history.push(credential); },
    async recordUsage(_username, usageGb) { state.active.usageGb = usageGb; },
    async close() {}
  };
  const service = createTurnService({
    metered,
    store,
    config: { ttlSeconds: 86400, rotationMs: 999999999, propagationMs: 0, usageIntervalMs: 999999999 },
    sleep: async () => {}
  });

  await service.start();
  assert.equal(calls.create, 1);
  assert.equal((await service.getIceServers())[0].urls, 'turn:api-1.example.test');
  assert.equal((await service.getStatus()).usageGb, 1.25);

  await service.rotate();
  assert.equal(calls.create, 2);
  assert.equal(state.history.length, 2);
  await service.stop();
});
