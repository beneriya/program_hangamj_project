# KR3 Web System

МУИС Компьютерын ухааны хөтөлбөрийн **Шалгуур 3** нотолгооны веб систем.

## Технологи
- **Backend**: Flask (Python 3.11) — REST API
- **Database**: MySQL 8.0 (Docker)
- **Frontend**: HTML + CSS (Bootstrap 5) + Vanilla JavaScript
- **Auth**: JWT (админ нэвтрэх)

## Архитектур
```
Frontend (HTML/JS)  ←→  Flask REST API  ←→  MySQL
        (static)         (:5000)              (:3307 → 3306)
```

Бүгд Docker Compose ашиглан 1 команда орчин бүрдүүлнэ.

## Хэрхэн ажиллуулах

### 1) Урьдчилсан нөхцөл
- Docker Desktop
- Docker Compose

### 2) Эхлүүлэх
```bash
cd web
docker compose up --build
```

Эхний ажиллагаа:
1. MySQL container эхэлнэ
2. Schema автоматаар үүснэ (`mysql-init/01_schema.sql`)
3. Flask backend эхэлнэ
4. Анхны ажиллах үед:
   - Анхдагч админ үүснэ (`admin` / `admin123`)
   - Seed өгөгдөл (18 шалгуур) автоматаар орно

### 3) Хандалт
- **Нүүр**: http://localhost:5000
- **Админ**: http://localhost:5000/login.html
  - username: `admin`
  - password: `admin123`

## REST API

| Method | Endpoint | Auth | Тайлбар |
|--------|----------|------|---------|
| GET | /api/items | — | Шалгуурын жагсаалт |
| GET | /api/items/:id | — | Дэлгэрэнгүй (tables + evidence) |
| POST | /api/admin/login | — | Нэвтрэх, token буцаана |
| POST | /api/items | ✔ | Шинэ шалгуур |
| PUT | /api/items/:id | ✔ | Засах |
| DELETE | /api/items/:id | ✔ | Устгах |
| POST | /api/items/:id/tables | ✔ | Хүснэгт нэмэх |
| PUT | /api/tables/:id | ✔ | Хүснэгт засах |
| DELETE | /api/tables/:id | ✔ | Хүснэгт устгах |
| POST | /api/items/:id/evidence | ✔ | Нотолгоо нэмэх |
| DELETE | /api/evidence/:id | ✔ | Нотолгоо устгах |
| POST | /api/upload | ✔ | Файл upload |

Auth хүссэн endpoint-д `Authorization: Bearer <token>` дамжуулна.

## Файлын бүтэц
```
web/
├── docker-compose.yml
├── mysql-init/
│   └── 01_schema.sql          # DB schema
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app.py                 # Flask + routes
│   ├── db.py                  # MySQL connection pool
│   ├── auth.py                # JWT + bcrypt
│   └── seed/
│       ├── kr3_data.json      # 18 шалгуурын raw өгөгдөл
│       └── load_seed.py       # seed loader
└── frontend/
    ├── index.html             # User: жагсаалт
    ├── item.html              # User: дэлгэрэнгүй
    ├── login.html             # Admin: нэвтрэх
    ├── admin.html             # Admin: dashboard
    ├── css/style.css
    └── js/
        ├── api.js             # REST client
        ├── main.js            # index
        ├── detail.js          # item
        ├── login.js           # login
        └── admin.js           # admin CRUD
```

## DB Schema

```
admins           - (id, username, password_hash)
kr3_items        - (id, title_mon, title_eng, verbatim, explanation, video_url, image_url, email_image_url, sort_order)
kr3_tables       - (id, item_id FK, title, rows_data JSON, sort_order)
kr3_evidence     - (id, item_id FK, label, file_path, sort_order)
```

`kr3_tables.rows_data` нь JSON — баганын бүтэц шалгуур бүрт өөр тул.

## Хөгжүүлэх

Reset DB (өгөгдөл дахин seed хийх):
```bash
docker compose down -v
docker compose up --build
```

Backend код өөрчлөх үед: `./backend` volume mount-тай тул автоматаар reload.

## Анхаарах

Production руу гаргахдаа заавал өөрчил:
- `JWT_SECRET` (docker-compose.yml)
- `ADMIN_PASSWORD`
- MySQL `MYSQL_ROOT_PASSWORD`, `MYSQL_PASSWORD`
