const BASE = (function(){
  // Centralized API base; can be changed for different environments
  if (typeof window !== 'undefined') {
    return window.__RAILAI_API_BASE__ || 'http://127.0.0.1:5000';
  }
  return 'http://127.0.0.1:5000';
})();

async function apiFetch(path, opts = {}){
  const url = `${BASE}${path}`;
  const headers = opts.headers || {};
  if (opts.body && !headers['Content-Type']) headers['Content-Type'] = 'application/json';
  const res = await fetch(url, { ...opts, headers });
  if (!res.ok) {
    const txt = await res.text().catch(()=>'');
    const err = new Error(`HTTP ${res.status} ${res.statusText}`);
    err.status = res.status;
    err.body = txt;
    throw err;
  }
  const ct = res.headers.get('content-type') || '';
  if (ct.includes('application/json')) return res.json();
  return res.text();
}

export { BASE, apiFetch };
