// Thin REST client used by all frontend pages.
const API = (() => {
  const base = window.location.origin; // same host serves API + frontend
  const TOKEN_KEY = "kr3_admin_token";
  const USER_KEY = "kr3_admin_user";

  function token() { return localStorage.getItem(TOKEN_KEY); }
  function setAuth(tok, user) {
    localStorage.setItem(TOKEN_KEY, tok);
    localStorage.setItem(USER_KEY, user);
  }
  function clearAuth() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }
  function user() { return localStorage.getItem(USER_KEY); }

  async function req(method, path, body, isForm) {
    const headers = {};
    if (!isForm) headers["Content-Type"] = "application/json";
    const t = token();
    if (t) headers["Authorization"] = "Bearer " + t;
    const opts = { method, headers };
    if (body !== undefined) {
      opts.body = isForm ? body : JSON.stringify(body);
    }
    const res = await fetch(base + path, opts);
    const txt = await res.text();
    let data = null;
    try { data = txt ? JSON.parse(txt) : null; } catch { data = txt; }
    if (!res.ok) {
      const err = new Error((data && data.error) || res.statusText || "Request failed");
      err.status = res.status;
      err.data = data;
      throw err;
    }
    return data;
  }

  return {
    token, user, setAuth, clearAuth,
    listItems: () => req("GET", "/api/items"),
    getItem: (id) => req("GET", `/api/items/${id}`),
    createItem: (body) => req("POST", "/api/items", body),
    updateItem: (id, body) => req("PUT", `/api/items/${id}`, body),
    deleteItem: (id) => req("DELETE", `/api/items/${id}`),
    addTable: (itemId, body) => req("POST", `/api/items/${itemId}/tables`, body),
    updateTable: (tableId, body) => req("PUT", `/api/tables/${tableId}`, body),
    deleteTable: (tableId) => req("DELETE", `/api/tables/${tableId}`),
    addEvidence: (itemId, body) => req("POST", `/api/items/${itemId}/evidence`, body),
    deleteEvidence: (evId) => req("DELETE", `/api/evidence/${evId}`),
    login: (username, password) => req("POST", "/api/admin/login", { username, password }),
    me: () => req("GET", "/api/admin/me"),
    upload: (file) => {
      const fd = new FormData();
      fd.append("file", file);
      return req("POST", "/api/upload", fd, true);
    },
  };
})();
