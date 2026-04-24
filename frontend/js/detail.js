(async function () {
  const root = document.getElementById("detail"); // Delgerengui medeelliin container
  const params = new URLSearchParams(window.location.search);
  const id = params.get("id"); // URL-aas shalguuriin ID-g awna
  if (!id) {
    // ID baihgui bol ankhaaruulga haruulna
    root.innerHTML = `<div class="alert alert-warning">ID байхгүй байна. <a href="/">Буцах</a></div>`;
    return;
  }

  // XSS-ees hamgaalah escape function
  function escapeHtml(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  // **bold** tegliig <strong> болгох, мөрийн таслалт хадгалана
  function formatExplanation(text) {
    if (!text) return "";
    return escapeHtml(text).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  }

  // Shalguuriin hustegtuudiig HTML hesegt bosgono
  function renderTables(tables) {
    if (!tables || tables.length === 0) return "";
    return tables
      .map((tbl) => {
        const rows = tbl.data || [];
        if (rows.length === 0) {
          return `<h4 class="section-title">${escapeHtml(tbl.title || "Хүснэгт")}</h4>
                  <p class="text-muted small">Мөр алга</p>`;
        }
        // Buh muriin key-uudees baganuudiig olno
        const cols = Array.from(
          rows.reduce((set, r) => {
            Object.keys(r || {}).forEach((k) => set.add(k));
            return set;
          }, new Set())
        );
        const head = cols.map((c) => `<th>${escapeHtml(c)}</th>`).join("");
        const body = rows
          .map(
            (r) =>
              `<tr>${cols
                .map((c) => `<td>${escapeHtml(r[c] ?? "")}</td>`)
                .join("")}</tr>`
          )
          .join("");
        return `
          <h4 class="section-title">${escapeHtml(tbl.title || "")}</h4>
          <div class="table-responsive">
            <table class="table table-striped table-bordered data-table">
              <thead><tr>${head}</tr></thead>
              <tbody>${body}</tbody>
            </table>
          </div>`;
      })
      .join("");
  }

  // Notolgoonuudiig HTML hesegt bosgono (file link bolgono)
  function renderEvidence(evs) {
    if (!evs || evs.length === 0) return "";
    return `
      <h4 class="section-title"><i class="bi bi-paperclip me-2"></i>Нотолгоо</h4>
      <div>${evs
        .map(
          (e) => `
          <a class="evidence-item" href="${e.file}" target="_blank" rel="noopener">
            <i class="bi bi-file-earmark-text"></i>
            <span>${escapeHtml(e.label || e.file)}</span>
            <i class="bi bi-box-arrow-up-right ms-auto text-muted"></i>
          </a>`
        )
        .join("")}</div>`;
  }

  try {
    // API-aas tuhain shalguuriin buren medeelliig tatna
    const it = await API.getItem(id);
    document.title = `${it.title_mon} — KR3`;

    // Video URL baival iframe uusgene
    const video = it.video_url
      ? `<div class="ratio ratio-16x9 mb-3"><iframe src="${escapeHtml(
          it.video_url
        )}" allowfullscreen></iframe></div>`
      : "";

    // Zurag URL baival img uusgene
    const image = it.image_url
      ? `<img src="${escapeHtml(it.image_url)}" class="img-fluid rounded mb-3" alt="" onerror="this.style.display='none'">`
      : "";

    // Email zurag baival haruulna
    const emailImg = it.email_image_url
      ? `<img src="${escapeHtml(it.email_image_url)}" class="img-fluid rounded mb-3 border" alt="" onerror="this.style.display='none'">`
      : "";

    // Buh hesgiin HTML-iig neg dotor ni baina
    root.innerHTML = `
      <div class="detail-card">
        <div class="d-flex align-items-center gap-2 text-muted small mb-2">
          <span class="chip">ID: ${it.id}</span>
        </div>
        <h2 class="fw-bold">${escapeHtml(it.title_mon)}</h2>
        <div class="verbatim-box">${escapeHtml(it.verbatim || "")}</div>
        ${video}
        ${image}
        <div class="explanation">${formatExplanation(it.explanation)}</div>
        ${emailImg}
        ${renderTables(it.tables)}
        ${renderEvidence(it.evidence)}
      </div>`;
  } catch (e) {
    // Aldaa garvaal hereglegchid medeelne
    root.innerHTML = `<div class="alert alert-danger">Алдаа: ${escapeHtml(
      e.message
    )}</div>`;
  }
})();
