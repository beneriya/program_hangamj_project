// Login form submit hiihde ajillana
document.getElementById("loginForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const u = document.getElementById("username").value.trim();
  const p = document.getElementById("password").value;
  const errBox = document.getElementById("loginError");
  errBox.classList.add("d-none"); // aldaa haruulah box-iig nuuna
  try {
    // Backend-d login huselt ilgeene
    const res = await API.login(u, p);
    // Token ba username-iig hadgalaad admin huudas ruu shiljine
    API.setAuth(res.token, res.username);
    window.location.href = "/admin.html";
  } catch (err) {
    // Aldaa garwal hereglegchid haruulna
    errBox.textContent = err.message || "Нэвтрэх үед алдаа гарлаа";
    errBox.classList.remove("d-none");
  }
});

// umnu ni nevterchihsen bol shuud admin ruu shiljine
if (API.token()) {
  API.me().then(() => (window.location.href = "/admin.html")).catch(() => API.clearAuth());
}
