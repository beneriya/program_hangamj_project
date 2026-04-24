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

# ---------------------------------------------------------------------------
# Үндсэн тохиргоо
# ---------------------------------------------------------------------------

# Одоогийн файлын байршил болон frontend/upload хавтасуудын замыг тодорхойлно
BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = Path("/frontend") if Path("/frontend").exists() else (BASE_DIR.parent / "frontend")
UPLOAD_DIR = BASE_DIR / "static" / "uploads"

# Байршуулах хавтас байхгүй бол автоматаар үүсгэнэ
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Flask апп үүсгэж, CORS-ийг идэвхжүүлнэ (өөр домэйнээс хандах зөвшөөрөл)
app = Flask(__name__, static_folder=None)
CORS(app)

# Зөвшөөрөгдсөн файлын өргөтгөлүүд
ALLOWED_EXT = {
    "pdf", "doc", "docx", "xls", "xlsx", "png", "jpg", "jpeg", "gif", "webp", "txt", "csv",
}


def allowed_file(filename: str) -> bool:
    """Файлын өргөтгөл зөвшөөрөгдсөн эсэхийг шалгана."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


def _init_admin():
    """
    Admins хүснэгт хоосон бол анхдагч admin хэрэглэгч үүсгэнэ.
    Нууц үг болон нэрийг орчны хувьсагчаас авна; тохируулаагүй бол
    'admin' / 'admin123' ашиглана — production орчинд заавал өөрчлөх хэрэгтэй!
    """
    username = os.getenv("ADMIN_USERNAME", "admin")
    password = os.getenv("ADMIN_PASSWORD", "admin123")
    conn = get_conn()
    try:
        cur = conn.cursor()
        # Admins хүснэгтэд хэдэн бичлэг байгааг тоолно
        cur.execute("SELECT COUNT(*) FROM admins")
        (n,) = cur.fetchone()
        if n == 0:
            # Хоосон байвал шинэ admin үүсгэж нууц үгийг hash хийж хадгална
            cur.execute(
                "INSERT INTO admins (username, password_hash) VALUES (%s, %s)",
                (username, hash_password(password)),
            )
            conn.commit()
            print(f"[init] анхдагч admin үүсгэлээ: {username}")
        cur.close()
    finally:
        conn.close()


def _seed_if_empty():
    """
    kr3_items хүснэгт хоосон бол туршилтын өгөгдөл (seed data) ачаална.
    Энэ нь эхний удаа апп ажиллуулахад л дуудагдана.
    """
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
            print("[init] seed өгөгдөл ачааллаа")
        except Exception as e:
            print(f"[init] seed алгасав: {e}")


# ---------------------------------------------------------------------------
# Статик файл болон frontend
# ---------------------------------------------------------------------------

@app.route("/")
def root():
    """Үндсэн хуудас — frontend-ийн index.html файлыг буцаана."""
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<path:path>")
def frontend_proxy(path):
    """
    Frontend-ийн статик файлуудыг (JS, CSS, зураг гэх мэт) дамжуулна.
    Файл олдохгүй бол SPA (Single Page App) тул index.html буцаана.
    """
    full = FRONTEND_DIR / path
    if full.is_file():
        return send_from_directory(FRONTEND_DIR, path)
    # Файл олдохгүй — SPA route-д зориулж index.html буцаана
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/uploads/<path:filename>")
def uploads(filename):
    """Байршуулсан файлуудыг /uploads/ замаар дамжуулна."""
    return send_from_directory(UPLOAD_DIR, filename)


# ---------------------------------------------------------------------------
# Туслах функцүүд
# ---------------------------------------------------------------------------

def item_row_to_dict(row):
    """
    Өгөгдлийн сангийн мөрийг API-д буцаах dict болгон хөрвүүлнэ.
    Зөвхөн шаардлагатай талбаруудыг оруулна.
    """
    return {
        "id": row["id"],
        "title_mon": row["title_mon"],       # Монгол гарчиг
        "title_eng": row["title_eng"],       # Англи гарчиг
        "verbatim": row["verbatim"],         # Эх бичвэр
        "explanation": row["explanation"],   # Тайлбар
        "video_url": row["video_url"],       # Видео холбоос
        "image_url": row["image_url"],       # Зургийн холбоос
        "email_image_url": row["email_image_url"],  # И-мэйл зургийн холбоос
        "sort_order": row["sort_order"],     # Эрэмбэлэх дараалал
    }


def get_item_full(item_id: int):
    """
    Тухайн item-ийн бүрэн мэдээллийг (хүснэгт болон нотлох баримттай хамт) авна.
    Олдохгүй бол None буцаана.
    """
    conn = get_conn()
    try:
        cur = conn.cursor(dictionary=True)

        # Үндсэн item мэдээлэл авна
        cur.execute("SELECT * FROM kr3_items WHERE id=%s", (item_id,))
        item = cur.fetchone()
        if not item:
            return None
        result = item_row_to_dict(item)

        # Энэ item-т харьяалагдах хүснэгтүүдийг дараалал бойлар авна
        cur.execute(
            "SELECT id, title, rows_data, sort_order FROM kr3_tables "
            "WHERE item_id=%s ORDER BY sort_order, id",
            (item_id,),
        )
        tables = []
        for r in cur.fetchall():
            raw = r["rows_data"]
            # bytes эсвэл bytearray байвал string болгоно
            if isinstance(raw, (bytes, bytearray)):
                raw = raw.decode("utf-8")
            # JSON string байвал parse хийнэ
            if isinstance(raw, str):
                try:
                    rows = json.loads(raw)
                except Exception:
                    rows = []  # Задлах боломжгүй бол хоосон жагсаалт
            else:
                rows = raw or []
            tables.append({
                "id": r["id"],
                "title": r["title"],
                "data": rows,
                "sort_order": r["sort_order"],
            })
        result["tables"] = tables

        # Нотлох баримт файлуудыг авна
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
# Нийтийн API (нэвтрэлт шаардахгүй)
# ---------------------------------------------------------------------------

@app.get("/api/items")
def list_items():
    """
    Бүх item-үүдийн жагсаалтыг буцаана.
    sort_order болон id-гаар эрэмбэлэгдсэн байна.
    """
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
    """
    Тухайн ID-тай item-ийн дэлгэрэнгүй мэдээллийг буцаана.
    Олдохгүй бол 404 алдаа буцаана.
    """
    item = get_item_full(item_id)
    if item is None:
        return jsonify({"error": "Олдсонгүй"}), 404
    return jsonify(item)


# ---------------------------------------------------------------------------
# Нэвтрэлт (Authentication)
# ---------------------------------------------------------------------------

@app.post("/api/admin/login")
def admin_login():
    """
    Admin нэвтрэх endpoint.
    Хэрэглэгчийн нэр болон нууц үг зөв байвал JWT токен буцаана.
    """
    body = request.get_json(silent=True) or {}
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""

    # Хэрэглэгчийн нэр эсвэл нууц үг хоосон бол алдаа буцаана
    if not username or not password:
        return jsonify({"error": "Хэрэглэгчийн нэр болон нууц үг шаардлагатай"}), 400

    conn = get_conn()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM admins WHERE username=%s", (username,))
        admin = cur.fetchone()
        cur.close()
    finally:
        conn.close()

    # Admin олдохгүй эсвэл нууц үг буруу бол 401 буцаана
    if not admin or not verify_password(password, admin["password_hash"]):
        return jsonify({"error": "Нэвтрэх мэдээлэл буруу байна"}), 401

    # Амжилттай нэвтэрвэл токен үүсгэж буцаана
    return jsonify({"token": create_token(username), "username": username})


@app.get("/api/admin/me")
@admin_required
def admin_me():
    """Одоо нэвтэрсэн admin-ийн хэрэглэгчийн нэрийг буцаана."""
    return jsonify({"username": request.admin_username})


# ---------------------------------------------------------------------------
# Admin CRUD — item удирдлага
# ---------------------------------------------------------------------------

@app.post("/api/items")
@admin_required
def create_item():
    """
    Шинэ item үүсгэнэ.
    title_mon талбар заавал шаардлагатай.
    """
    body = request.get_json(silent=True) or {}
    if not body.get("title_mon"):
        return jsonify({"error": "title_mon талбар шаардлагатай"}), 400

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
                body.get("sort_order", 0),  # Дараалал өгөгдөөгүй бол 0
            ),
        )
        new_id = cur.lastrowid  # Шинээр үүсгэсэн бичлэгийн ID
        conn.commit()
        cur.close()
    finally:
        conn.close()
    return jsonify(get_item_full(new_id)), 201


@app.put("/api/items/<int:item_id>")
@admin_required
def update_item(item_id):
    """
    Тухайн ID-тай item-ийн мэдээллийг шинэчилнэ.
    Зөвхөн body-д ирсэн талбаруудыг л шинэчилнэ (partial update).
    """
    body = request.get_json(silent=True) or {}
    fields = [
        "title_mon", "title_eng", "verbatim", "explanation",
        "video_url", "image_url", "email_image_url", "sort_order",
    ]

    # Шинэчлэх талбар болон утгуудыг динамикаар бэлдэнэ
    sets = []
    values = []
    for f in fields:
        if f in body:
            sets.append(f"{f}=%s")
            values.append(body[f])

    if not sets:
        return jsonify({"error": "Шинэчлэх талбар байхгүй байна"}), 400

    values.append(item_id)
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(f"UPDATE kr3_items SET {', '.join(sets)} WHERE id=%s", values)
        if cur.rowcount == 0:
            cur.close()
            return jsonify({"error": "Олдсонгүй"}), 404
        conn.commit()
        cur.close()
    finally:
        conn.close()
    return jsonify(get_item_full(item_id))


@app.delete("/api/items/<int:item_id>")
@admin_required
def delete_item(item_id):
    """
    Тухайн ID-тай item-ийг устгана.
    Олдохгүй бол 404 буцаана.
    """
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM kr3_items WHERE id=%s", (item_id,))
        found = cur.rowcount > 0  # Устгасан мөр байсан эсэх
        conn.commit()
        cur.close()
    finally:
        conn.close()
    if not found:
        return jsonify({"error": "Олдсонгүй"}), 404
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Admin CRUD — хүснэгт удирдлага (item дотор)
# ---------------------------------------------------------------------------

@app.post("/api/items/<int:item_id>/tables")
@admin_required
def add_table(item_id):
    """
    Тухайн item-д шинэ хүснэгт нэмнэ.
    data талбар нь мөрүүдийн массив байх ёстой.
    """
    body = request.get_json(silent=True) or {}
    title = body.get("title") or ""
    rows = body.get("data") or []

    if not isinstance(rows, list):
        return jsonify({"error": "data нь массив байх ёстой"}), 400

    conn = get_conn()
    try:
        cur = conn.cursor()
        # Эхлээд item байгаа эсэхийг шалгана
        cur.execute("SELECT id FROM kr3_items WHERE id=%s", (item_id,))
        if cur.fetchone() is None:
            cur.close()
            return jsonify({"error": "Item олдсонгүй"}), 404

        # Хүснэгтийн өгөгдлийг JSON хэлбэрт хөрвүүлж хадгална
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
    """
    Тухайн хүснэгтийн гарчиг, өгөгдөл эсвэл дарааллыг шинэчилнэ.
    Зөвхөн ирсэн талбаруудыг л өөрчилнэ.
    """
    body = request.get_json(silent=True) or {}
    conn = get_conn()
    try:
        cur = conn.cursor(dictionary=True)
        # Хүснэгт байгаа эсэх болон харьяалагдах item_id-г авна
        cur.execute("SELECT item_id FROM kr3_tables WHERE id=%s", (table_id,))
        row = cur.fetchone()
        if not row:
            cur.close()
            return jsonify({"error": "Олдсонгүй"}), 404
        item_id = row["item_id"]

        sets = []
        values = []
        if "title" in body:
            sets.append("title=%s")
            values.append(body["title"])
        if "data" in body:
            # Хүснэгтийн мөрүүдийг JSON болгон хадгална
            sets.append("rows_data=%s")
            values.append(json.dumps(body["data"], ensure_ascii=False))
        if "sort_order" in body:
            sets.append("sort_order=%s")
            values.append(body["sort_order"])

        if not sets:
            cur.close()
            return jsonify({"error": "Шинэчлэх талбар байхгүй байна"}), 400

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
    """Тухайн хүснэгтийг устгаад, харьяалах item-ийн шинэчлэгдсэн мэдээллийг буцаана."""
    conn = get_conn()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT item_id FROM kr3_tables WHERE id=%s", (table_id,))
        row = cur.fetchone()
        if not row:
            cur.close()
            return jsonify({"error": "Олдсонгүй"}), 404
        item_id = row["item_id"]
        cur.execute("DELETE FROM kr3_tables WHERE id=%s", (table_id,))
        conn.commit()
        cur.close()
    finally:
        conn.close()
    return jsonify(get_item_full(item_id))


# ---------------------------------------------------------------------------
# Admin CRUD — нотлох баримт удирдлага
# ---------------------------------------------------------------------------

@app.post("/api/items/<int:item_id>/evidence")
@admin_required
def add_evidence(item_id):
    """
    Тухайн item-д нотлох баримт файл нэмнэ.
    label — харуулах нэр, file — файлын зам.
    """
    body = request.get_json(silent=True) or {}
    label = body.get("label") or ""
    file_path = body.get("file") or ""

    conn = get_conn()
    try:
        cur = conn.cursor()
        # Item байгаа эсэхийг эхлээд шалгана
        cur.execute("SELECT id FROM kr3_items WHERE id=%s", (item_id,))
        if cur.fetchone() is None:
            cur.close()
            return jsonify({"error": "Item олдсонгүй"}), 404

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
    """Нотлох баримтыг устгаад, харьяалах item-ийн шинэчлэгдсэн мэдээллийг буцаана."""
    conn = get_conn()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT item_id FROM kr3_evidence WHERE id=%s", (ev_id,))
        row = cur.fetchone()
        if not row:
            cur.close()
            return jsonify({"error": "Олдсонгүй"}), 404
        item_id = row["item_id"]
        cur.execute("DELETE FROM kr3_evidence WHERE id=%s", (ev_id,))
        conn.commit()
        cur.close()
    finally:
        conn.close()
    return jsonify(get_item_full(item_id))


# ---------------------------------------------------------------------------
# Файл байршуулах
# ---------------------------------------------------------------------------

@app.post("/api/upload")
@admin_required
def upload():
    """
    Файл байршуулах endpoint.
    - Файлын өргөтгөлийг шалгана (зөвшөөрөгдсөн жагсаалттай харьцуулна)
    - Давхардлаас сэргийлж uuid ашиглан өвөрмөц нэр өгнө
    - Амжилттай бол файлын замыг буцаана
    """
    if "file" not in request.files:
        return jsonify({"error": "Файл олдсонгүй"}), 400

    f = request.files["file"]
    if not f or not f.filename:
        return jsonify({"error": "Файл сонгоогүй байна"}), 400

    # Зөвшөөрөгдсөн өргөтгөл эсэхийг шалгана
    if not allowed_file(f.filename):
        return jsonify({"error": "Энэ төрлийн файл зөвшөөрөгдөөгүй"}), 400

    # Аюулгүй файлын нэр үүсгэнэ (path traversal халдлагаас хамгаална)
    safe = secure_filename(f.filename)
    if not safe:
        safe = "file"

    # uuid ашиглан давхардахгүй өвөрмөц нэр үүсгэнэ
    unique = f"{uuid.uuid4().hex[:8]}_{safe}"
    dest = UPLOAD_DIR / unique
    f.save(dest)

    return jsonify({"path": f"/uploads/{unique}", "filename": safe})


# ---------------------------------------------------------------------------
# Апп эхлүүлэх
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _init_admin()       # Анхдагч admin үүсгэнэ (хэрэв байхгүй бол)
    _seed_if_empty()    # Туршилтын өгөгдөл ачаална (хэрэв хоосон бол)
    app.run(host="0.0.0.0", port=4000, debug=True)
