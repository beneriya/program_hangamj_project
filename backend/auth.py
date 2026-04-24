import os
import datetime
import jwt
import bcrypt
from functools import wraps
from flask import request, jsonify

# JWT token-ii nuguts ug - production deer zaawl .env-ees awna
JWT_SECRET = os.getenv("JWT_SECRET", "dev_secret")
JWT_ALGO = "HS256"
JWT_EXP_HOURS = 12  # token 12 tsagiin daraa hugatsaa duusna


def hash_password(password: str) -> str:
    # Nuuts ug-iig bcrypt-eer kodlono - database-d energy hadgalna
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    # Hereglegchiin oruulsan nuuts ug database-d baidag hash-tai taarchaad esehiig shalgana
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


def create_token(username: str) -> str:
    # Amjilttai login hiisen ued JWT token uusgene
    payload = {
        "sub": username,  # token-d hereglegchiin ner hadgalna
        "exp": datetime.datetime.now(datetime.timezone.utc)
        + datetime.timedelta(hours=JWT_EXP_HOURS),  # hugatsaa duusah tsag
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


def decode_token(token: str):
    # Token-iig shiifriin tailt bolgoж hereglegchiin medeelliig awna
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])


def admin_required(f):
    # Decorator: zuwhun admin neverchsen humuus l ugsaan route-d oroltsoh bolomt'oi
    @wraps(f)
    def wrapper(*args, **kwargs):
        # Authorization header-ees token aw
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401
        token = auth_header[7:]
        try:
            payload = decode_token(token)
            request.admin_username = payload.get("sub")  # username-iig request-d hadgalna
        except jwt.ExpiredSignatureError:
            # Token hugatsaa ni duussaniig hariu ilgeene
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            # Buruu token irseniig hariu ilgeene
            return jsonify({"error": "Invalid token"}), 401
        return f(*args, **kwargs)

    return wrapper
