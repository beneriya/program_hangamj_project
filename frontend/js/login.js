document.getElementById("loginForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const u = document.getElementById("username").value.trim();
  const p = document.getElementById("password").value;
  const errBox = document.getElementById("loginError");
  errBox.classList.add("d-none");
  try {
    const res = await API.login(u, p);
    API.setAuth(res.token, res.username);
    window.location.href = "/admin.html";
  } catch (err) {
    errBox.textContent = err.message || "Нэвтрэх үед алдаа гарлаа";
    errBox.classList.remove("d-none");
  }
});

// If already logged in, go straight to admin
if (API.token()) {
  API.me().then(() => (window.location.href = "/admin.html")).catch(() => API.clearAuth());
}
