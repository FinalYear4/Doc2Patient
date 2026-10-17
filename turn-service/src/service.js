const DEFAULT_TTL_SECONDS = 24 * 60 * 60;
const DEFAULT_ROTATION_MS = 12 * 60 * 60 * 1000;
const DEFAULT_PROPAGATION_MS = 2 * 60 * 1000;

export function createTurnService({ metered, store, config = {}, sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms)) }) {
  const ttlSeconds = Number(config.ttlSeconds || DEFAULT_TTL_SECONDS);
  const rotationMs = Number(config.rotationMs || DEFAULT_ROTATION_MS);
  const propagationMs = Number(config.propagationMs || DEFAULT_PROPAGATION_MS);
  const label = config.label || 'doc2patient-production';
  let active = null;
  let rotationTimer = null;
  let usageTimer = null;

  function expiresSoon(credential) {
    return !credential || new Date(credential.expiresAt).getTime() - Date.now() < 5 * 60 * 1000;
  }

  async function createAndActivate() {
    const created = await metered.createCredential({ expiryInSeconds: ttlSeconds, label });
    const credential = {
      username: created.username,
      apiKey: created.apiKey,
      label: created.label || label,
      expiresAt: new Date(Date.now() + ttlSeconds * 1000).toISOString(),
      iceServers: null
    };
    credential.iceServers = await metered.getIceServers(credential.apiKey);
    await sleep(propagationMs);
    await store.activate(credential);
    active = credential;
    return credential;
  }

  async function ensureActive() {
    if (!active) active = await store.getActive();
    if (expiresSoon(active)) active = await createAndActivate();
    if (!active.iceServers) active.iceServers = await metered.getIceServers(active.apiKey);
    return active;
  }

  async function rotate() {
    try {
      await createAndActivate();
    } catch (error) {
      console.error('TURN credential rotation failed:', error.message);
    }
  }

  async function monitorUsage() {
    if (!active) return;
    try {
      const usage = await metered.getUsage(active.username);
      const usageGb = Number(usage.usageInGB ?? usage.usageInGb ?? 0);
      active.usageGb = usageGb;
      await store.recordUsage(active.username, usageGb);
    } catch (error) {
      console.error('TURN usage check failed:', error.message);
    }
  }

  async function start() {
    await store.init();
    await ensureActive();
    rotationTimer = setInterval(rotate, rotationMs);
    usageTimer = setInterval(monitorUsage, Number(config.usageIntervalMs || 15 * 60 * 1000));
    await monitorUsage();
  }

  async function stop() {
    if (rotationTimer) clearInterval(rotationTimer);
    if (usageTimer) clearInterval(usageTimer);
    await store.close();
  }

  async function getIceServers() {
    const credential = await ensureActive();
    return credential.iceServers;
  }

  async function getStatus() {
    const credential = await ensureActive();
    return {
      username: credential.username,
      label: credential.label,
      expiresAt: credential.expiresAt,
      usageGb: credential.usageGb ?? null
    };
  }

  return { start, stop, getIceServers, getStatus, rotate };
}
