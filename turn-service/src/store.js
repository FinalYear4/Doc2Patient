import pg from 'pg';

const { Pool } = pg;

export function createStore({ databaseUrl }) {
  let pool = null;
  const memory = { active: null, history: [] };

  if (databaseUrl) {
    pool = new Pool({ connectionString: databaseUrl, ssl: { rejectUnauthorized: false } });
  }

  async function init() {
    if (!pool) return;
    await pool.query(`
      CREATE TABLE IF NOT EXISTS turn_credentials (
        id BIGSERIAL PRIMARY KEY,
        username TEXT NOT NULL,
        api_key TEXT NOT NULL,
        label TEXT NOT NULL,
        expires_at TIMESTAMPTZ NOT NULL,
        usage_gb DOUBLE PRECISION,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        active BOOLEAN NOT NULL DEFAULT FALSE
      )
    `);
  }

  async function getActive() {
    if (!pool) return memory.active;
    const result = await pool.query(
      'SELECT username, api_key, label, expires_at, usage_gb FROM turn_credentials WHERE active = TRUE ORDER BY created_at DESC LIMIT 1'
    );
    const row = result.rows[0];
    if (!row) return null;
    return {
      username: row.username,
      apiKey: row.api_key,
      label: row.label,
      expiresAt: row.expires_at,
      usageGb: row.usage_gb
    };
  }

  async function activate(credential) {
    if (!pool) {
      memory.active = credential;
      memory.history.push(credential);
      return;
    }
    await pool.query('UPDATE turn_credentials SET active = FALSE WHERE active = TRUE');
    await pool.query(
      `INSERT INTO turn_credentials (username, api_key, label, expires_at, active)
       VALUES ($1, $2, $3, $4, TRUE)`,
      [credential.username, credential.apiKey, credential.label, credential.expiresAt]
    );
  }

  async function recordUsage(username, usageGb) {
    if (!pool) {
      const item = memory.history.find((entry) => entry.username === username);
      if (item) item.usageGb = usageGb;
      return;
    }
    await pool.query(
      'UPDATE turn_credentials SET usage_gb = $1 WHERE username = $2',
      [usageGb, username]
    );
  }

  async function close() {
    if (pool) await pool.end();
  }

  return { init, getActive, activate, recordUsage, close };
}
