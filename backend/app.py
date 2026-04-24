import os
import json
import uuid
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory, abort
from flask_cors import CORS
from werkzeug.utils import secure_filename

from db import get_conn
from auth import (
    hash_password,
    verify_password,
    create_token,
    admin_required,
)

# Fayliin zamуудыг togtoono
BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = Path("/frontend") if Path("/frontend").exists() else (BASE_DIR.parent / "frontend")
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)  # uploads folder baihgui bol uusgene

app = Flask(__name__, static_folder=None)
CORS(app)  # frontend өөр port-oos nemeh ued CORS aldaanaas sergiilen idewhjuulne

# Зөвшөөрөгдсөн файлын төрлүүд
ALLOWED_EXT = {
    "pdf", "doc", "docx", "xls", "xlsx", "png", "jpg", "jpeg", "gif", "webp", "txt", "csv",
}


def allowed_file(filename: str) -> bool:
    # Fayliin extension zuvshurugtei esehiig shalgana
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


def _init_admin():
    # Admins husnegt khоgson bol default admin uusgene
    username = os.getenv("ADMIN_USERNAME", "admin")
    password = os.getenv("ADMIN_PASSWORD", "admin123")
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM admins")
        (n,) = cur.fetchone()
        if n == 0:
            # Odoogoor admin baikhgui bol shine admin nemne
            cur.execute(
                "INSERT INTO admins (username, password_hash) VALUES (%s, %s)",
                (username, hash_password(password)),
            )
            conn.commit()
            print(f"[init] default admin created: {username}")
        cur.close()
    finally:
        conn.close()


def _seed_if_empty():
    # kr3_items khоgson bol test data achaalat
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM kr3_items")
        (n,) = cur.fetchone()
        cur.close()
    finally:
        conn.close()
    if n == 0:
        try:
            from seed.load_seed import run_seed
            run_seed()
            print("[init] seed data loaded")
        except Exception as e:
            print(f"[init] seed skipped: {e}")


# ---------------------------------------------------------------------------
# Frontend fayluudiig ilgeeh route-uud
# ---------------------------------------------------------------------------

@app.route("/")
def root():
    # Nuuts huudasiig butsaana
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<path:path>")
def frontend_proxy(path):
    # Bусад frontend fayluudiig (css, js, html) ilgeene
    full = FRONTEND_DIR / path
    if full.is_file():
        return send_from_directory(FRONTEND_DIR, path)
    # Fayl oldsongui bol index.html ruу hariu ilgeene
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/uploads/<path:filename>")
def uploads(filename):
    # Upload hiigdsen fayluudiig butsaana
    return send_from_directory(UPLOAD_DIR, filename)


# ---------------------------------------------------------------------------
# Допomогч функцуud
# ---------------------------------------------------------------------------

def item_row_to_dict(row):
    # Database-iin мөрийг dict болгоно
    return {
        "id": row["id"],
        "title_mon": row["title_mon"],
        "title_eng": row["title_eng"],
        "verbatim": row["verbatim"],
        "explanation": row["explanation"],
        "video_url": row["video_url"],
        "image_url": row["image_url"],
        "email_image_url": row["email_image_url"],
        "sort_order": row["sort_order"],
    }


def get_item_full(item_id: int):
    # Нэг item-ийн бүрэн мэдээллийг (хүснэгт, нотолгоотой) татна
    conn = get_conn()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM kr3_items WHERE id=%s", (item_id,))
        item = cur.fetchone()
        if not item:
            return None
        result = item_row_to_dict(item)

        # Тухайн item-д холбоотой хүснэгтүүдийг татна
        cur.execute(
            "SELECT id, title, rows_data, sort_order FROM kr3_tables "
            "WHERE item_id=%s ORDER BY sort_order, id",
            (item_id,),
        )
        tables = []
        for r in cur.fetchall():
            raw = r["rows_data"]
            if isinstance(raw, (bytes, bytearray)):
                raw = raw.decode("utf-8")
            if isinstance(raw, str):
                try:
                    rows = json.loads(raw)  # JSON string-iig list болгоно
                except Exception:
                    rows = []
            else:
                rows = raw or []
            tables.append({
                "id": r["id"],
                "title": r["title"],
                "data": rows,
                "sort_order": r["sort_order"],
            })
        result["tables"] = tables

        # Тухайн item-д холбоотой нотолгоонуудыг татна
        cur.execute(
            "SELECT id, label, file_path, sort_order FROM kr3_evidence "
            "WHERE item_id=%s ORDER BY sort_order, id",
            (item_id,),
        )
        result["evidence"] = [
            {"id": r["id"], "label": r["label"], "file": r["file_path"], "sort_order": r["sort_order"]}
            for r in cur.fetchall()
        ]
        cur.close()
        return result
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Нийтийн API (login шаардахгүй)
# ---------------------------------------------------------------------------

@app.get("/api/items")
def list_items():
    # Бүх шалгуурын жагсаалтыг буцаана
    conn = get_conn()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT id, title_mon, title_eng, verbatim, sort_order "
            "FROM kr3_items ORDER BY sort_order, id"
        )
        rows = cur.fetchall()
        cur.close()
    finally:
        conn.close()
    return jsonify(rows)


@app.get("/api/items/<int:item_id>")
def get_item(item_id):
    # Нэг шалгуурын дэлгэрэнгүй мэдээллийг буцаана
    item = get_item_full(item_id)
    if item is None:
        return jsonify({"error": "Not found"}), 404
    return jsonify(item)


# ---------------------------------------------------------------------------
# Нэвтрэлт
# ---------------------------------------------------------------------------

@app.post("/api/admin/login")
def admin_login():
    # Admin login: username/password шалган JWT token буцаана
    body = request.get_json(silent=True) or {}
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""
    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400
    conn = get_conn()
    try:
        cur = conn.cursor(dictionary=True)
        # Username-aar admin хайна
        cur.execute("SELECT * FROM admins WHERE username=%s", (username,))
        admin = cur.fetchone()
        cur.close()
    finally:
        conn.close()
    if not admin or not verify_password(password, admin["password_hash"]):
        # Admin олдсонгүй эсвэл нууц үг буруу
        return jsonify({"error": "Invalid credentials"}), 401
    return jsonify({"token": create_token(username), "username": username})


@app.get("/api/admin/me")
@admin_required
def admin_me():
    # Одоогийн нэвтэрсэн admin-ийн мэдээллийг буцаана
    return jsonify({"username": request.admin_username})


# ---------------------------------------------------------------------------
# Admin CRUD - шалгуурууд
# ---------------------------------------------------------------------------

@app.post("/api/items")
@admin_required
def create_item():
    # Шинэ шалгуур үүсгэнэ (admin эрх шаардана)
    body = request.get_json(silent=True) or {}
    if not body.get("title_mon"):
        return jsonify({"error": "title_mon is required"}), 400
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO kr3_items
               (title_mon, title_eng, verbatim, explanation, video_url,
                image_url, email_image_url, sort_order)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                body.get("title_mon"),
                body.get("title_eng"),
                body.get("verbatim"),
                body.get("explanation"),
                body.get("video_url"),
                body.get("image_url"),
                body.get("email_image_url"),
                body.get("sort_order", 0),
            ),
        )
        new_id = cur.lastrowid  # Шинэ мөрийн ID-г авна
        conn.commit()
        cur.close()
    finally:
        conn.close()
    return jsonify(get_item_full(new_id)), 201


@app.put("/api/items/<int:item_id>")
@admin_required
def update_item(item_id):
    # Шалгуурын мэдээллийг шинэчилнэ (зөвхөн ирсэн талбаруудыг)
    body = request.get_json(silent=True) or {}
    fields = [
        "title_mon", "title_eng", "verbatim", "explanation",
        "video_url", "image_url", "email_image_url", "sort_order",
    ]
    sets = []
    values = []
    for f in fields:
        if f in body:
            sets.append(f"{f}=%s")
            values.append(body[f])
    if not sets:
        return jsonify({"error": "no fields to update"}), 400
    values.append(item_id)
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(f"UPDATE kr3_items SET {', '.join(sets)} WHERE id=%s", values)
        if cur.rowcount == 0:
            cur.close()
            return jsonify({"error": "Not found"}), 404
        conn.commit()
        cur.close()
    finally:
        conn.close()
    return jsonify(get_item_full(item_id))


@app.delete("/api/items/<int:item_id>")
@admin_required
def delete_item(item_id):
    # Шалгуурыг устгана (холбоотой хүснэгт, нотолгоо мөн устана)
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM kr3_items WHERE id=%s", (item_id,))
        found = cur.rowcount > 0
        conn.commit()
        cur.close()
    finally:
        conn.close()
    if not found:
        return jsonify({"error": "Not found"}), 404
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Admin CRUD - хүснэгтүүд (item-д хамаарах)
# ---------------------------------------------------------------------------

@app.post("/api/items/<int:item_id>/tables")
@admin_required
def add_table(item_id):
    # Шалгуурт шинэ хүснэгт нэмнэ
    body = request.get_json(silent=True) or {}
    title = body.get("title") or ""
    rows = body.get("data") or []
    if not isinstance(rows, list):
        return jsonify({"error": "data must be an array of row objects"}), 400
    conn = get_conn()
    try:
        cur = conn.cursor()
        # Эхлээд item байгаа эсэхийг шалгана
        cur.execute("SELECT id FROM kr3_items WHERE id=%s", (item_id,))
        if cur.fetchone() is None:
            cur.close()
            return jsonify({"error": "item not found"}), 404
        cur.execute(
            "INSERT INTO kr3_tables (item_id, title, rows_data, sort_order) VALUES (%s, %s, %s, %s)",
            (item_id, title, json.dumps(rows, ensure_ascii=False), body.get("sort_order", 0)),
        )
        conn.commit()
        cur.close()
    finally:
        conn.close()
    return jsonify(get_item_full(item_id)), 201


@app.put("/api/tables/<int:table_id>")
@admin_required
def update_table(table_id):
    # Хүснэгтийн мэдээллийг шинэчилнэ
    body = request.get_json(silent=True) or {}
    conn = get_conn()
    try:
        cur = conn.cursor(dictionary=True)
        # Хүснэгт аль item-д хамаарахыг олно
        cur.execute("SELECT item_id FROM kr3_tables WHERE id=%s", (table_id,))
        row = cur.fetchone()
        if not row:
            cur.close()
            return jsonify({"error": "Not found"}), 404
        item_id = row["item_id"]
        sets = []
        values = []
        if "title" in body:
            sets.append("title=%s")
            values.append(body["title"])
        if "data" in body:
            sets.append("rows_data=%s")
            values.append(json.dumps(body["data"], ensure_ascii=False))
        if "sort_order" in body:
            sets.append("sort_order=%s")
            values.append(body["sort_order"])
        if not sets:
            cur.close()
            return jsonify({"error": "no fields to update"}), 400
        values.append(table_id)
        cur.execute(f"UPDATE kr3_tables SET {', '.join(sets)} WHERE id=%s", values)
        conn.commit()
        cur.close()
    finally:
        conn.close()
    return jsonify(get_item_full(item_id))


@app.delete("/api/tables/<int:table_id>")
@admin_required
def delete_table(table_id):
    # Хүснэгтийг устгана
    conn = get_conn()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT item_id FROM kr3_tables WHERE id=%s", (table_id,))
        row = cur.fetchone()
        if not row:
            cur.close()
            return jsonify({"error": "Not found"}), 404
        item_id = row["item_id"]
        cur.execute("DELETE FROM kr3_tables WHERE id=%s", (table_id,))
        conn.commit()
        cur.close()
    finally:
        conn.close()
    return jsonify(get_item_full(item_id))


# ---------------------------------------------------------------------------
# Admin CRUD - нотолгоо
# ---------------------------------------------------------------------------

@app.post("/api/items/<int:item_id>/evidence")
@admin_required
def add_evidence(item_id):
    # Шалгуурт нотолгоо (файл) нэмнэ
    body = request.get_json(silent=True) or {}
    label = body.get("label") or ""
    file_path = body.get("file") or ""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM kr3_items WHERE id=%s", (item_id,))
        if cur.fetchone() is None:
            cur.close()
            return jsonify({"error": "item not found"}), 404
        cur.execute(
            "INSERT INTO kr3_evidence (item_id, label, file_path, sort_order) VALUES (%s, %s, %s, %s)",
            (item_id, label, file_path, body.get("sort_order", 0)),
        )
        conn.commit()
        cur.close()
    finally:
        conn.close()
    return jsonify(get_item_full(item_id)), 201


@app.delete("/api/evidence/<int:ev_id>")
@admin_required
def delete_evidence(ev_id):
    # Нотолгоог устгана
    conn = get_conn()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT item_id FROM kr3_evidence WHERE id=%s", (ev_id,))
        row = cur.fetchone()
        if not row:
            cur.close()
            return jsonify({"error": "Not found"}), 404
        item_id = row["item_id"]
        cur.execute("DELETE FROM kr3_evidence WHERE id=%s", (ev_id,))
        conn.commit()
        cur.close()
    finally:
        conn.close()
    return jsonify(get_item_full(item_id))


# ---------------------------------------------------------------------------
# Файл upload
# ---------------------------------------------------------------------------

@app.post("/api/upload")
@admin_required
def upload():
    # Файл хүлээн авч /uploads/ folder-т хадгална
    if "file" not in request.files:
        return jsonify({"error": "no file part"}), 400
    f = request.files["file"]
    if not f or not f.filename:
        return jsonify({"error": "no selected file"}), 400
    if not allowed_file(f.filename):
        return jsonify({"error": "file type not allowed"}), 400
    safe = secure_filename(f.filename)  # Аюулгүй файлын нэр үүсгэнэ
    if not safe:
        safe = "file"
    unique = f"{uuid.uuid4().hex[:8]}_{safe}"  # Давхардахгүйн тулд random нэр нэмнэ
    dest = UPLOAD_DIR / unique
    f.save(dest)
    return jsonify({"path": f"/uploads/{unique}", "filename": safe})


# ---------------------------------------------------------------------------
# Эхлүүлэх
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _init_admin()      # Default admin байхгүй бол үүсгэнэ
    _seed_if_empty()   # Мэдээлэл хоосон бол seed data ачаална
    app.run(host="0.0.0.0", port=5000, debug=True)
