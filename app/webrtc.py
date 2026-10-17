import time

import requests

from app import app


_ice_cache = {'expires_at': 0, 'servers': None}


def get_ice_servers():
    """Return browser-safe ICE servers without exposing service credentials."""
    now = time.time()
    if _ice_cache['servers'] and _ice_cache['expires_at'] > now:
        return _ice_cache['servers']

    servers = [
        {'urls': ['stun:stun.l.google.com:19302', 'stun:stun1.l.google.com:19302']}
    ]
    service_url = app.config.get('TURN_SERVICE_URL')
    service_token = app.config.get('TURN_SERVICE_TOKEN')

    if service_url and service_token:
        try:
            response = requests.get(
                f"{service_url.rstrip('/')}/internal/ice-servers",
                headers={'X-Turn-Service-Token': service_token},
                timeout=app.config.get('TURN_SERVICE_TIMEOUT_SECONDS', 5),
            )
            response.raise_for_status()
            dynamic_servers = response.json().get('iceServers', [])
            if isinstance(dynamic_servers, list):
                servers.extend(dynamic_servers)
        except (requests.RequestException, ValueError) as error:
            app.logger.warning('TURN service unavailable; using STUN only: %s', error)
    elif app.config.get('WEBRTC_TURN_URL'):
        servers.append({
            'urls': app.config['WEBRTC_TURN_URL'],
            'username': app.config.get('WEBRTC_TURN_USERNAME'),
            'credential': app.config.get('WEBRTC_TURN_CREDENTIAL'),
        })

    _ice_cache['servers'] = servers
    _ice_cache['expires_at'] = now + 60
    return servers
