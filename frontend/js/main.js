(async function () {
  // Nuuts huudasnii DOM elementuudiig awna
  const listEl = document.getElementById("itemsList");    // Shalguuriig haruulah container
  const countEl = document.getElementById("countBadge");  // Toо haruulah badge
  const searchEl = document.getElementById("searchInput"); // Hailtiig talbar

  let items = []; // API-aas tatsan buh shalguuruud

  // Shalguuriig filter hiij HTML-d haruulna
  function render(filter = "") {
    const q = filter.trim().toLowerCase();
    const filtered = q
      ? items.filter((it) =>
          (it.title_mon || "").toLowerCase().includes(q) ||
          (it.verbatim || "").toLowerCase().includes(q)  // Mongol garchig ba verbatim-aar shuur
        )
      : items;

    // Shalguuriin too-iig badge-d haruulna
    countEl.textContent = `${filtered.length} шалгуур`;
    if (filtered.length === 0) {
      listEl.innerHTML = `<div class="col-12 text-center text-muted py-5">Илэрц олдсонгүй</div>`;
      return;
    }
    // Shalguur tus buriin card HTML uusgene
    listEl.innerHTML = filtered
      .map(
        (it, idx) => `
        <div class="col-md-6 col-lg-4">
          <a class="item-card" href="/item.html?id=${it.id}">
            <div class="item-number">${idx + 1}</div>
            <h5>${escapeHtml(it.title_mon)}</h5>
            <div class="verbatim">${escapeHtml(it.verbatim || "")}</div>
          </a>
        </div>`
      )
      .join("");
  }

  // XSS-ees hamgaalah escape function
  function escapeHtml(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  try {
    // API-aas buh shalguuriig tatna
    items = await API.listItems();
    render(); // Filtergui buh shalguuriig haruulna
  } catch (e) {
    // Aldaa garvaal hereglegchid medeelne
    listEl.innerHTML = `<div class="col-12"><div class="alert alert-danger">Алдаа: ${e.message}</div></div>`;
  }

  // Hailtiig talbart utga oruulahad shalguuriig shine shuurna
  if (searchEl) {
    searchEl.addEventListener("input", (e) => render(e.target.value));
  }
})();
