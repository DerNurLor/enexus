const BASE = '';
let _token = '';
let _reAuthPromise: Promise<boolean> | null = null;

export function setToken(t: string) {
  _token = t;
}

async function _reAuth(): Promise<boolean> {
  if (_reAuthPromise) return _reAuthPromise;
  _reAuthPromise = (async () => {
    try {
      const initData = window.Telegram?.WebApp?.initData;
      if (!initData) return false;
      const res = await fetch(`${BASE}/miniapp/auth`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ init_data: initData }),
      });
      if (!res.ok) return false;
      const data = await res.json();
      _token = data.token;
      return true;
    } catch {
      return false;
    } finally {
      _reAuthPromise = null;
    }
  })();
  return _reAuthPromise;
}

export async function api<T = unknown>(
  url: string,
  opts: RequestInit = {},
  _retry = true
): Promise<T> {
  const res = await fetch(BASE + url, {
    ...opts,
    headers: {
      'Content-Type': 'application/json',
      Authorization: _token ? `Bearer ${_token}` : '',
      ...(opts.headers as Record<string, string> || {}),
    },
  });

  if (res.status === 401 && _retry) {
    const ok = await _reAuth();
    if (ok) return api<T>(url, opts, false);
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({})) as { detail?: string };
    throw new Error(err.detail || `HTTP ${res.status}`);
  }

  return res.json() as Promise<T>;
}
