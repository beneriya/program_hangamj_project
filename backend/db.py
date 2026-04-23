import os
import time
import mysql.connector
from mysql.connector import pooling

_pool = None


def get_pool():
    global _pool
    if _pool is None:
        for attempt in range(30):
            try:
                _pool = pooling.MySQLConnectionPool(
                    pool_name="kr3_pool",
                    pool_size=5,
                    host=os.getenv("DB_HOST", "mysql"),
                    port=int(os.getenv("DB_PORT", "3306")),
                    database=os.getenv("DB_NAME", "kr3db"),
                    user=os.getenv("DB_USER", "kr3user"),
                    password=os.getenv("DB_PASSWORD", "kr3pass"),
                    charset="utf8mb4",
                    use_unicode=True,
                    autocommit=False,
                )
                break
            except mysql.connector.Error as e:
                print(f"[db] waiting for mysql ({attempt+1}/30): {e}")
                time.sleep(2)
        if _pool is None:
            raise RuntimeError("Could not connect to MySQL after retries")
    return _pool


def get_conn():
    return get_pool().get_connection()
