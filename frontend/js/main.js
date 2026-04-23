(async function () {
  const listEl = document.getElementById("itemsList");
  const countEl = document.getElementById("countBadge");
  const searchEl = document.getElementById("searchInput");

  let items = [];

  function render(filter = "") {
    const q = filter.trim().toLowerCase();
    const filtered = q
      ? items.filter((it) =>
          (it.title_mon || "").toLowerCase().includes(q) ||
          (it.verbatim || "").toLowerCase().includes(q)
        )
      : items;

    countEl.textContent = `${filtered.length} шалгуур`;
    if (filtered.length === 0) {
      listEl.innerHTML = `<div class="col-12 text-center text-muted py-5">Илэрц олдсонгүй</div>`;
      return;
    }
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

  function escapeHtml(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  try {
    items = await API.listItems();
    render();
  } catch (e) {
    listEl.innerHTML = `<div class="col-12"><div class="alert alert-danger">Алдаа: ${e.message}</div></div>`;
  }

  if (searchEl) {
    searchEl.addEventListener("input", (e) => render(e.target.value));
  }
})();
