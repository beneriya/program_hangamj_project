// ---------------------------------------------------------------------------
// Auth guard
// ---------------------------------------------------------------------------
if (!API.token()) {
  window.location.href = "/login.html";
}

document.getElementById("adminUser").textContent = API.user() || "";
document.getElementById("logoutBtn").addEventListener("click", () => {
  API.clearAuth();
  window.location.href = "/login.html";
});

const state = {
  items: [],
  current: null, // full item with tables+evidence
};

const listEl = document.getElementById("adminList");
const editorEl = document.getElementById("editorArea");
const searchEl = document.getElementById("adminSearch");
const toastArea = document.getElementById("toastArea");

// ---------------------------------------------------------------------------
// Utilities
// ---------------------------------------------------------------------------
function esc(s) {
  return String(s || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function toast(msg, kind = "success") {
  const id = "t" + Date.now();
  const bg = { success: "bg-success", danger: "bg-danger", warning: "bg-warning" }[kind] || "bg-secondary";
  const el = document.createElement("div");
  el.className = `toast align-items-center text-white border-0 ${bg}`;
  el.id = id;
  el.role = "alert";
  el.innerHTML = `<div class="d-flex">
    <div class="toast-body">${esc(msg)}</div>
    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
  </div>`;
  toastArea.appendChild(el);
  const t = new bootstrap.Toast(el, { delay: 3000 });
  t.show();
  el.addEventListener("hidden.bs.toast", () => el.remove());
}

async function handle(fn) {
  try { return await fn(); }
  catch (e) {
    if (e.status === 401) {
      API.clearAuth();
      window.location.href = "/login.html";
      return;
    }
    toast(e.message || "Алдаа гарлаа", "danger");
    throw e;
  }
}

// ---------------------------------------------------------------------------
// Sidebar list
// ---------------------------------------------------------------------------
async function refreshList() {
  state.items = await handle(() => API.listItems());
  renderList();
}

function renderList(filter = "") {
  const q = filter.trim().toLowerCase();
  const items = q
    ? state.items.filter((i) => (i.title_mon || "").toLowerCase().includes(q))
    : state.items;
  listEl.innerHTML = items
    .map(
      (i) => `
      <button class="list-group-item list-group-item-action ${state.current && state.current.id === i.id ? "active-item" : ""}" data-id="${i.id}">
        <div class="fw-semibold" style="white-space: normal;">${esc(i.title_mon)}</div>
      </button>`
    )
    .join("");
  listEl.querySelectorAll("[data-id]").forEach((el) => {
    el.addEventListener("click", () => loadItem(+el.dataset.id));
  });
}

searchEl.addEventListener("input", (e) => renderList(e.target.value));

// ---------------------------------------------------------------------------
// Editor
// ---------------------------------------------------------------------------
async function loadItem(id) {
  state.current = await handle(() => API.getItem(id));
  renderEditor();
  renderList(searchEl.value);
}

function emptyItem() {
  return {
    id: null,
    title_mon: "",
    title_eng: "",
    verbatim: "",
    explanation: "",
    video_url: "",
    image_url: "",
    email_image_url: "",
    tables: [],
    evidence: [],
  };
}

function renderEditor() {
  const it = state.current;
  if (!it) {
    editorEl.innerHTML = "";
    return;
  }
  const isNew = !it.id;
  editorEl.innerHTML = `
    <div class="editor-section">
      <div class="d-flex justify-content-between align-items-center mb-3">
        <h6 class="mb-0">${isNew ? "Шинэ шалгуур" : `Шалгуур #${it.id}`}</h6>
        ${!isNew ? `<button class="btn btn-outline-danger btn-sm" id="deleteItemBtn"><i class="bi bi-trash"></i> Устгах</button>` : ""}
      </div>
      <div class="row g-3">
        <div class="col-md-6">
          <label class="form-label">Гарчиг (Монгол) *</label>
          <input class="form-control" id="fTitleMon" value="${esc(it.title_mon)}" />
        </div>
        <div class="col-md-6">
          <label class="form-label">Гарчиг (Англи)</label>
          <input class="form-control" id="fTitleEng" value="${esc(it.title_eng)}" />
        </div>
        <div class="col-12">
          <label class="form-label">Verbatim (эх текст)</label>
          <textarea class="form-control" id="fVerbatim" rows="2">${esc(it.verbatim)}</textarea>
        </div>
        <div class="col-12">
          <label class="form-label">Тайлбар (explanation)</label>
          <textarea class="form-control" id="fExplanation" rows="8">${esc(it.explanation)}</textarea>
          <div class="form-text">** bold ** дэмжигдэнэ. Мөр таслах: enter.</div>
        </div>
        <div class="col-md-6">
          <label class="form-label">Video URL (embed)</label>
          <input class="form-control" id="fVideo" value="${esc(it.video_url)}" />
        </div>
        <div class="col-md-6">
          <label class="form-label">Image URL</label>
          <div class="input-group">
            <input class="form-control" id="fImage" value="${esc(it.image_url)}" />
            <button class="btn btn-outline-secondary" type="button" data-upload="fImage"><i class="bi bi-upload"></i></button>
          </div>
        </div>
        <div class="col-md-6">
          <label class="form-label">Email image URL</label>
          <div class="input-group">
            <input class="form-control" id="fEmail" value="${esc(it.email_image_url)}" />
            <button class="btn btn-outline-secondary" type="button" data-upload="fEmail"><i class="bi bi-upload"></i></button>
          </div>
        </div>
      </div>
      <div class="mt-3">
        <button class="btn btn-primary" id="saveItemBtn"><i class="bi bi-check-lg me-1"></i>Хадгалах</button>
      </div>
    </div>

    ${!isNew ? tablesBlock(it) + evidenceBlock(it) : `<div class="alert alert-info">Эхлээд шалгуурыг хадгалсны дараа хүснэгт, нотолгоо нэмэх боломжтой.</div>`}
  `;

  wireEditorEvents(isNew);
}

function tablesBlock(it) {
  const list = (it.tables || [])
    .map(
      (t) => `
      <div class="border rounded p-2 mb-2 d-flex justify-content-between align-items-center">
        <div>
          <strong>${esc(t.title || "(гарчиггүй)")}</strong>
          <span class="text-muted small">— ${(t.data || []).length} мөр</span>
        </div>
        <div class="btn-group btn-group-sm">
          <button class="btn btn-outline-primary" data-edit-table="${t.id}"><i class="bi bi-pencil"></i></button>
          <button class="btn btn-outline-danger" data-del-table="${t.id}"><i class="bi bi-trash"></i></button>
        </div>
      </div>`
    )
    .join("");
  return `
    <div class="editor-section">
      <div class="d-flex justify-content-between align-items-center mb-2">
        <h6 class="mb-0"><i class="bi bi-table me-2"></i>Хүснэгтүүд</h6>
        <button class="btn btn-sm btn-outline-primary" id="addTableBtn"><i class="bi bi-plus-lg"></i> Шинэ хүснэгт</button>
      </div>
      ${list || `<p class="text-muted small mb-0">Хүснэгт алга</p>`}
    </div>`;
}

function evidenceBlock(it) {
  const list = (it.evidence || [])
    .map(
      (e) => `
      <div class="border rounded p-2 mb-2 d-flex justify-content-between align-items-center">
        <div class="text-truncate" style="max-width: 80%;">
          <i class="bi bi-file-earmark-text text-danger me-2"></i>
          <strong>${esc(e.label)}</strong>
          <span class="text-muted small d-block">${esc(e.file)}</span>
        </div>
        <button class="btn btn-sm btn-outline-danger" data-del-ev="${e.id}"><i class="bi bi-trash"></i></button>
      </div>`
    )
    .join("");
  return `
    <div class="editor-section">
      <div class="d-flex justify-content-between align-items-center mb-2">
        <h6 class="mb-0"><i class="bi bi-paperclip me-2"></i>Нотолгоо</h6>
        <button class="btn btn-sm btn-outline-primary" id="addEvBtn"><i class="bi bi-plus-lg"></i> Нэмэх</button>
      </div>
      <div class="row g-2 mb-2" id="addEvRow" style="display:none;">
        <div class="col-md-5">
          <input class="form-control form-control-sm" id="evLabel" placeholder="Нэр (label)" />
        </div>
        <div class="col-md-5">
          <input class="form-control form-control-sm" id="evFile" placeholder="/path/to/file.pdf" />
        </div>
        <div class="col-md-2 d-flex gap-1">
          <button class="btn btn-sm btn-outline-secondary" id="evUploadBtn" title="Файл upload"><i class="bi bi-upload"></i></button>
          <button class="btn btn-sm btn-success" id="evSaveBtn"><i class="bi bi-check"></i></button>
        </div>
      </div>
      ${list || `<p class="text-muted small mb-0">Нотолгоо алга</p>`}
    </div>`;
}

function wireEditorEvents(isNew) {
  document.getElementById("saveItemBtn").addEventListener("click", saveItem);
  if (!isNew) {
    document.getElementById("deleteItemBtn")?.addEventListener("click", deleteItem);
    document.getElementById("addTableBtn")?.addEventListener("click", () => openTableModal(null));
    document.getElementById("addEvBtn")?.addEventListener("click", () => {
      document.getElementById("addEvRow").style.display = "flex";
    });
    document.getElementById("evSaveBtn")?.addEventListener("click", addEvidence);
    document.getElementById("evUploadBtn")?.addEventListener("click", () => pickAndUpload("evFile"));
    editorEl.querySelectorAll("[data-edit-table]").forEach((el) =>
      el.addEventListener("click", () => openTableModal(+el.dataset.editTable))
    );
    editorEl.querySelectorAll("[data-del-table]").forEach((el) =>
      el.addEventListener("click", () => deleteTable(+el.dataset.delTable))
    );
    editorEl.querySelectorAll("[data-del-ev]").forEach((el) =>
      el.addEventListener("click", () => deleteEvidence(+el.dataset.delEv))
    );
  }
  editorEl.querySelectorAll("[data-upload]").forEach((btn) =>
    btn.addEventListener("click", () => pickAndUpload(btn.dataset.upload))
  );
}

async function saveItem() {
  const body = {
    title_mon: document.getElementById("fTitleMon").value.trim(),
    title_eng: document.getElementById("fTitleEng").value.trim(),
    verbatim: document.getElementById("fVerbatim").value,
    explanation: document.getElementById("fExplanation").value,
    video_url: document.getElementById("fVideo").value.trim(),
    image_url: document.getElementById("fImage").value.trim(),
    email_image_url: document.getElementById("fEmail").value.trim(),
  };
  if (!body.title_mon) return toast("Гарчиг заавал бөглөгдөнө", "warning");
  const saved = state.current.id
    ? await handle(() => API.updateItem(state.current.id, body))
    : await handle(() => API.createItem(body));
  state.current = saved;
  await refreshList();
  renderEditor();
  toast("Хадгаллаа");
}

async function deleteItem() {
  if (!confirm("Энэ шалгуурыг устгах уу? Холбоотой хүснэгт, нотолгоо мөн устана.")) return;
  await handle(() => API.deleteItem(state.current.id));
  state.current = null;
  await refreshList();
  editorEl.innerHTML = `<div class="text-muted text-center py-5">Устгагдлаа</div>`;
  toast("Устгагдлаа");
}

// ---------------------------------------------------------------------------
// Evidence
// ---------------------------------------------------------------------------
async function addEvidence() {
  const label = document.getElementById("evLabel").value.trim();
  const file = document.getElementById("evFile").value.trim();
  if (!label || !file) return toast("Label ба файлын зам бөглөнө үү", "warning");
  state.current = await handle(() =>
    API.addEvidence(state.current.id, { label, file })
  );
  renderEditor();
  toast("Нотолгоо нэмэгдлээ");
}

async function deleteEvidence(id) {
  if (!confirm("Энэ нотолгоог устгах уу?")) return;
  state.current = await handle(() => API.deleteEvidence(id));
  renderEditor();
  toast("Устгагдлаа");
}

// ---------------------------------------------------------------------------
// Upload helper
// ---------------------------------------------------------------------------
function pickAndUpload(targetInputId) {
  const input = document.createElement("input");
  input.type = "file";
  input.addEventListener("change", async () => {
    if (!input.files[0]) return;
    const res = await handle(() => API.upload(input.files[0]));
    if (res && res.path) {
      document.getElementById(targetInputId).value = res.path;
      toast("Файл upload хийгдлээ");
    }
  });
  input.click();
}

// ---------------------------------------------------------------------------
// Table modal (inline editor)
// ---------------------------------------------------------------------------
const tableModalEl = document.getElementById("tableModal");
const tableModal = new bootstrap.Modal(tableModalEl);
let tableState = { id: null, title: "", columns: [], rows: [] };

function openTableModal(tableId) {
  if (tableId) {
    const tbl = (state.current.tables || []).find((t) => t.id === tableId);
    if (!tbl) return;
    const cols = Array.from(
      (tbl.data || []).reduce((s, r) => {
        Object.keys(r || {}).forEach((k) => s.add(k));
        return s;
      }, new Set())
    );
    tableState = {
      id: tbl.id,
      title: tbl.title || "",
      columns: cols.length ? cols : ["Багана 1"],
      rows: JSON.parse(JSON.stringify(tbl.data || [])),
    };
  } else {
    tableState = { id: null, title: "", columns: ["Багана 1", "Багана 2"], rows: [{}] };
  }
  document.getElementById("tblTitle").value = tableState.title;
  renderTableEditor();
  tableModal.show();
}

function renderTableEditor() {
  const thead = document.querySelector("#tblEditor thead");
  const tbody = document.querySelector("#tblEditor tbody");
  thead.innerHTML =
    "<tr>" +
    tableState.columns
      .map(
        (c, i) => `
      <th style="min-width: 160px;">
        <div class="input-group input-group-sm">
          <input class="form-control form-control-sm col-name" data-idx="${i}" value="${esc(c)}" />
          <button class="btn btn-outline-danger" data-del-col="${i}"><i class="bi bi-x"></i></button>
        </div>
      </th>`
      )
      .join("") +
    `<th style="width:40px;"></th></tr>`;

  tbody.innerHTML = tableState.rows
    .map(
      (row, rIdx) => `
      <tr>
        ${tableState.columns
          .map(
            (c) => `
            <td><input class="form-control form-control-sm cell" data-r="${rIdx}" data-c="${esc(c)}" value="${esc(row[c] ?? "")}" /></td>`
          )
          .join("")}
        <td class="text-center"><button class="btn btn-sm btn-outline-danger" data-del-row="${rIdx}"><i class="bi bi-trash"></i></button></td>
      </tr>`
    )
    .join("");

  thead.querySelectorAll(".col-name").forEach((inp) => {
    inp.addEventListener("input", (e) => {
      const i = +e.target.dataset.idx;
      const oldName = tableState.columns[i];
      const newName = e.target.value;
      // rename column in each row
      tableState.rows = tableState.rows.map((r) => {
        const nr = { ...r };
        if (oldName in nr) {
          nr[newName] = nr[oldName];
          if (oldName !== newName) delete nr[oldName];
        }
        return nr;
      });
      tableState.columns[i] = newName;
    });
  });
  thead.querySelectorAll("[data-del-col]").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      const i = +e.currentTarget.dataset.delCol;
      const name = tableState.columns[i];
      tableState.columns.splice(i, 1);
      tableState.rows = tableState.rows.map((r) => {
        const nr = { ...r };
        delete nr[name];
        return nr;
      });
      renderTableEditor();
    });
  });
  tbody.querySelectorAll(".cell").forEach((inp) => {
    inp.addEventListener("input", (e) => {
      const r = +e.target.dataset.r;
      const c = e.target.dataset.c;
      tableState.rows[r][c] = e.target.value;
    });
  });
  tbody.querySelectorAll("[data-del-row]").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      const r = +e.currentTarget.dataset.delRow;
      tableState.rows.splice(r, 1);
      renderTableEditor();
    });
  });
}

document.getElementById("tblAddCol").addEventListener("click", () => {
  tableState.columns.push(`Багана ${tableState.columns.length + 1}`);
  renderTableEditor();
});
document.getElementById("tblAddRow").addEventListener("click", () => {
  const empty = {};
  tableState.columns.forEach((c) => (empty[c] = ""));
  tableState.rows.push(empty);
  renderTableEditor();
});
document.getElementById("tblSave").addEventListener("click", async () => {
  tableState.title = document.getElementById("tblTitle").value;
  const body = { title: tableState.title, data: tableState.rows };
  if (tableState.id) {
    state.current = await handle(() => API.updateTable(tableState.id, body));
  } else {
    state.current = await handle(() => API.addTable(state.current.id, body));
  }
  tableModal.hide();
  renderEditor();
  toast("Хадгалагдлаа");
});

async function deleteTable(id) {
  if (!confirm("Хүснэгтийг устгах уу?")) return;
  state.current = await handle(() => API.deleteTable(id));
  renderEditor();
  toast("Устгагдлаа");
}

// ---------------------------------------------------------------------------
// Toolbar
// ---------------------------------------------------------------------------
document.getElementById("newItemBtn").addEventListener("click", () => {
  state.current = emptyItem();
  renderEditor();
  renderList(searchEl.value);
});

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------
(async function () {
  try {
    await API.me();
  } catch {
    API.clearAuth();
    window.location.href = "/login.html";
    return;
  }
  await refreshList();
})();
