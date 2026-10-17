import 'dotenv/config';
import express from 'express';
import { createMeteredClient } from './metered-client.js';
import { createStore } from './store.js';
import { createTurnService } from './service.js';

const config = {
  appName: process.env.METERED_APP_NAME,
  secretKey: process.env.METERED_SECRET_KEY,
  serviceToken: process.env.TURN_SERVICE_TOKEN,
  ttlSeconds: Number(process.env.METERED_CREDENTIAL_TTL_SECONDS || 86400),
  rotationMs: Number(process.env.METERED_ROTATION_INTERVAL_MS || 43200000),
  propagationMs: Number(process.env.METERED_PROPAGATION_DELAY_MS || 120000),
  usageIntervalMs: Number(process.env.METERED_USAGE_INTERVAL_MS || 900000),
  label: process.env.METERED_CREDENTIAL_LABEL || 'doc2patient-production'
};

if (!config.serviceToken) {
  throw new Error('TURN_SERVICE_TOKEN is required');
}

const metered = createMeteredClient(config);
const store = createStore({ databaseUrl: process.env.DATABASE_URL });
const turn = createTurnService({ metered, store, config });
const app = express();
const port = Number(process.env.PORT || 3000);

function requireServiceToken(request, response, next) {
  if (!config.serviceToken || request.get('x-turn-service-token') !== config.serviceToken) {
    return response.status(401).json({ error: 'Unauthorized' });
  }
  next();
}

app.get('/healthz', (_request, response) => response.json({ ok: true }));

app.get('/internal/ice-servers', requireServiceToken, async (_request, response) => {
  try {
    response.json({ iceServers: await turn.getIceServers() });
  } catch (error) {
    console.error('ICE server request failed:', error.message);
    response.status(503).json({ error: 'TURN service unavailable' });
  }
});

app.get('/internal/status', requireServiceToken, async (_request, response) => {
  try {
    response.json(await turn.getStatus());
  } catch (error) {
    console.error('TURN status request failed:', error.message);
    response.status(503).json({ error: 'TURN service unavailable' });
  }
});

const server = app.listen(port, async () => {
  try {
    await turn.start();
    console.log(`TURN service listening on port ${port}`);
  } catch (error) {
    console.error('TURN service failed to start:', error.message);
    process.exitCode = 1;
    server.close();
  }
});

async function shutdown() {
  await turn.stop();
  server.close(() => process.exit(0));
}

process.on('SIGTERM', shutdown);
process.on('SIGINT', shutdown);
