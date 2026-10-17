const apiRoot = (appName) => `https://${appName}.metered.live/api/v1/turn`;

async function parseResponse(response) {
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = body.message || body.error || response.statusText;
    throw new Error(`Metered API ${response.status}: ${detail}`);
  }
  return body;
}

export function createMeteredClient({ appName, secretKey, fetchImpl = fetch }) {
  if (!appName || !secretKey) {
    throw new Error('METERED_APP_NAME and METERED_SECRET_KEY are required');
  }

  return {
    async createCredential({ expiryInSeconds, label }) {
      const response = await fetchImpl(
        `${apiRoot(appName)}/credential?secretKey=${encodeURIComponent(secretKey)}`,
        {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({ expiryInSeconds, label })
        }
      );
      return parseResponse(response);
    },

    async getIceServers(apiKey) {
      const response = await fetchImpl(
        `${apiRoot(appName)}/credentials?apiKey=${encodeURIComponent(apiKey)}`
      );
      return parseResponse(response);
    },

    async getUsage(username) {
      const response = await fetchImpl(
        `${apiRoot(appName)}/current_usage_for_user?secretKey=${encodeURIComponent(secretKey)}&username=${encodeURIComponent(username)}`
      );
      return parseResponse(response);
    }
  };
}
