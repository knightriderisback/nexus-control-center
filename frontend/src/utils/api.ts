/**
 * NEXUS Centralized API Bridge & Client Utilities.
 * Handles dynamic bridge URL configuration, token authentication,
 * and unified WebSocket / REST connectivity without hardcoded secrets.
 */

export interface BridgeConfig {
  bridgeUrl: string;
  apiKey: string;
}

const BRIDGE_URL_KEY = 'nexus_bridge_url';
const API_KEY_KEY = 'nexus_api_key';

export function getApiBaseUrl(): string {
  if (typeof window === 'undefined') return '';
  const stored = localStorage.getItem(BRIDGE_URL_KEY);
  if (stored && stored.trim()) {
    return stored.trim().replace(/\/+$/, '');
  }
  // Default to relative root if on localhost/127.0.0.1
  const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
  if (isLocal) {
    return '';
  }
  return '';
}

export function setApiBaseUrl(url: string): void {
  if (typeof window === 'undefined') return;
  const clean = url.trim().replace(/\/+$/, '');
  if (clean) {
    localStorage.setItem(BRIDGE_URL_KEY, clean);
  } else {
    localStorage.removeItem(BRIDGE_URL_KEY);
  }
}

export function getNexusApiKey(): string {
  if (typeof window === 'undefined') return '';
  return localStorage.getItem(API_KEY_KEY) || '';
}

export function setNexusApiKey(key: string): void {
  if (typeof window === 'undefined') return;
  const clean = key.trim();
  if (clean) {
    localStorage.setItem(API_KEY_KEY, clean);
  } else {
    localStorage.removeItem(API_KEY_KEY);
  }
}

export function getWsUrl(): string {
  if (typeof window === 'undefined') return 'ws://127.0.0.1:8000/ws';
  const baseUrl = getApiBaseUrl();
  const token = getNexusApiKey();
  const tokenQuery = token ? `?token=${encodeURIComponent(token)}` : '';

  if (baseUrl) {
    const wsProto = baseUrl.startsWith('https:') ? 'wss:' : 'ws:';
    const host = baseUrl.replace(/^https?:\/\//, '');
    return `${wsProto}//${host}/ws${tokenQuery}`;
  }

  const wsProto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${wsProto}//${window.location.host}/ws${tokenQuery}`;
}

export async function nexusFetch<T = any>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const base = getApiBaseUrl();
  const cleanPath = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  const fullUrl = `${base}${cleanPath}`;

  const headers = new Headers(options.headers || {});
  
  const apiKey = getNexusApiKey();
  if (apiKey && !headers.has('X-NEXUS-KEY')) {
    headers.set('X-NEXUS-KEY', apiKey);
  }
  if (!headers.has('Accept')) {
    headers.set('Accept', 'application/json');
  }
  if (options.body && typeof options.body === 'string' && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const res = await fetch(fullUrl, {
    ...options,
    headers
  });

  if (!res.ok) {
    let errorDetail = `HTTP ${res.status} ${res.statusText}`;
    try {
      const errJson = await res.json();
      errorDetail = errJson.detail || errJson.message || errorDetail;
    } catch {
      // ignore JSON parse fail
    }
    throw new Error(errorDetail);
  }

  return res.json();
}

export interface BridgeHealthCheckResult {
  ok: boolean;
  status: string;
  latencyMs: number;
  osEnvironment?: string;
  isTermux?: boolean;
  projectsCount?: number;
  error?: string;
}

export async function testBridgeHealth(targetUrl?: string, testKey?: string): Promise<BridgeHealthCheckResult> {
  const base = (targetUrl !== undefined ? targetUrl : getApiBaseUrl()).trim().replace(/\/+$/, '');
  const key = testKey !== undefined ? testKey : getNexusApiKey();
  const checkUrl = `${base}/api/v1/connector/status`;

  const t0 = performance.now();
  try {
    const headers: Record<string, string> = { 'Accept': 'application/json' };
    if (key) {
      headers['X-NEXUS-KEY'] = key;
    }

    const res = await fetch(checkUrl, {
      method: 'GET',
      headers,
      signal: AbortSignal.timeout(5000)
    });

    const latency = Math.round(performance.now() - t0);

    if (!res.ok) {
      return {
        ok: false,
        status: `HTTP_${res.status}`,
        latencyMs: latency,
        error: `Server responded with ${res.status} ${res.statusText}`
      };
    }

    const data = await res.json();
    return {
      ok: true,
      status: data.status || 'ONLINE',
      latencyMs: latency,
      osEnvironment: data.os_environment,
      isTermux: data.is_termux,
      projectsCount: data.connected_projects_count
    };
  } catch (err: any) {
    const latency = Math.round(performance.now() - t0);
    return {
      ok: false,
      status: 'UNREACHABLE',
      latencyMs: latency,
      error: err.name === 'TimeoutError' ? 'Connection timed out (5s)' : err.message || 'Network error'
    };
  }
}
