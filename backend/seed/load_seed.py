import json
from pathlib import Path
from db import get_conn

HERE = Path(__file__).resolve().parent
DATA_FILE = HERE / "kr3_data.json"


def run_seed():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    conn = get_conn()
    try:
        cur = conn.cursor()
        for idx, item in enumerate(data):
            cur.execute(
                """INSERT INTO kr3_items
                   (title_mon, title_eng, verbatim, explanation, video_url,
                    image_url, email_image_url, sort_order)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    item.get("title_mon"),
                    item.get("title_eng"),
                    item.get("verbatim"),
                    item.get("explanation"),
                    item.get("videoUrl"),
                    item.get("imageUrl"),
                    item.get("emailImageUrl"),
                    idx,
                ),
            )
            item_id = cur.lastrowid

            for t_idx, tbl in enumerate(item.get("tables", []) or []):
                cur.execute(
                    "INSERT INTO kr3_tables (item_id, title, rows_data, sort_order) VALUES (%s, %s, %s, %s)",
                    (
                        item_id,
                        tbl.get("title"),
                        json.dumps(tbl.get("data", []), ensure_ascii=False),
                        t_idx,
                    ),
                )

            for e_idx, ev in enumerate(item.get("evidence", []) or []):
                cur.execute(
                    "INSERT INTO kr3_evidence (item_id, label, file_path, sort_order) VALUES (%s, %s, %s, %s)",
                    (item_id, ev.get("label"), ev.get("file"), e_idx),
                )

        conn.commit()
        cur.close()
    finally:
        conn.close()


if __name__ == "__main__":
    run_seed()
    print("seed: done")
