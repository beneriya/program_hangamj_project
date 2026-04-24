// Buh frontend huudas ashigladаg API client
const API = (() => {
  const base = window.location.origin; // API ba frontend neg host deer ajillana
  const TOKEN_KEY = "kr3_admin_token";  // localStorage-d token hadgalah 
  const USER_KEY = "kr3_admin_user";    // localStorage-d username hadgalah

  // Token-iig localStorage-s awna
  function token() { return localStorage.getItem(TOKEN_KEY); }

  // Login amjilttai bol token ba username hadgalna
  function setAuth(tok, user) {
    localStorage.setItem(TOKEN_KEY, tok);
    localStorage.setItem(USER_KEY, user);
  }

  // Logout hiihde token ustgana
  function clearAuth() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }

  // Odoogoor nevtersan hereglegchiin ner
  function user() { return localStorage.getItem(USER_KEY); }

  // Buh API-d ildegdeh suuri fetch function
  async function req(method, path, body, isForm) {
    const headers = {};
    if (!isForm) headers["Content-Type"] = "application/json";
    const t = token();
    // Token baival Authorization header nemne
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
      // Server aldaa butsaawal exception hiine
      const err = new Error((data && data.error) || res.statusText || "Request failed");
      err.status = res.status;
      err.data = data;
      throw err;
    }
    return data;
  }

  // Gadagsh ilreh API methoduud
  return {
    token, user, setAuth, clearAuth,
    listItems: () => req("GET", "/api/items"),                              // Buh shalguuriig avna
    getItem: (id) => req("GET", `/api/items/${id}`),                       // Negen shalguuriig avna
    createItem: (body) => req("POST", "/api/items", body),                 // Shine shalguur uusgene
    updateItem: (id, body) => req("PUT", `/api/items/${id}`, body),        // Shalguuriig shinechlene
    deleteItem: (id) => req("DELETE", `/api/items/${id}`),                 // Shalguuriig ustgana
    addTable: (itemId, body) => req("POST", `/api/items/${itemId}/tables`, body),  // Husnegt nemne
    updateTable: (tableId, body) => req("PUT", `/api/tables/${tableId}`, body),    // Husnegt shinechlene
    deleteTable: (tableId) => req("DELETE", `/api/tables/${tableId}`),             // Husnegt ustgana
    addEvidence: (itemId, body) => req("POST", `/api/items/${itemId}/evidence`, body), // Notolgo nemne
    deleteEvidence: (evId) => req("DELETE", `/api/evidence/${evId}`),              // Notolgo ustgana
    login: (username, password) => req("POST", "/api/admin/login", { username, password }), // Login
    me: () => req("GET", "/api/admin/me"),                                 // Odoogiin admin info
    upload: (file) => {
      // File upload hiihde FormData ashiglana
      const fd = new FormData();
      fd.append("file", file);
      return req("POST", "/api/upload", fd, true);
    },
  };
})();
