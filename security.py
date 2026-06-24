"""
Лёгкие защитные механизмы, перенесённые из оригинального oldmarket-server.
"""
from datetime import datetime, date, timedelta

from database import fetch_one, execute_query

async def ensure_security_tables():
    await execute_query("""
    CREATE TABLE IF NOT EXISTS registration_ip (
        ip TEXT NOT NULL,
        day TEXT NOT NULL,
        count INTEGER DEFAULT 0,
        PRIMARY KEY (ip, day)
    )
    """)
    await execute_query("""
    CREATE TABLE IF NOT EXISTS login_attempt (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ip TEXT NOT NULL,
        username TEXT,
        success INTEGER NOT NULL,
        created_at TEXT NOT NULL
    )
    """)
    await execute_query("""
    CREATE TABLE IF NOT EXISTS blocked_ip (
        ip TEXT PRIMARY KEY,
        reason TEXT NOT NULL,
        until TEXT NOT NULL
    )
    """)
    await execute_query("""
    CREATE TABLE IF NOT EXISTS download_ip (
        app_id INTEGER NOT NULL,
        ip TEXT NOT NULL,
        created_at TEXT NOT NULL,
        PRIMARY KEY (app_id, ip)
    )
    """)
    await execute_query("""
    CREATE TABLE IF NOT EXISTS submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        author TEXT NOT NULL,
        category_code TEXT NOT NULL,
        data JSON NOT NULL,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

def get_real_ip(request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return (
        request.headers.get("cf-connecting-ip")
        or request.headers.get("x-real-ip")
        or (request.client.host if request.client else "unknown")
    )

async def is_ip_blocked(ip: str) -> bool:
    if not ip:
        return False
    row = await fetch_one("SELECT until FROM blocked_ip WHERE ip = ?", (ip,))
    if not row:
        return False
    if datetime.fromisoformat(row["until"]) <= datetime.utcnow():
        await execute_query("DELETE FROM blocked_ip WHERE ip = ?", (ip,))
        return False
    return True

async def ban_ip(ip: str, reason: str, hours: int = 1):
    if not ip:
        return
    until = (datetime.utcnow() + timedelta(hours=hours)).isoformat()
    await execute_query(
        "INSERT INTO blocked_ip (ip, reason, until) VALUES (?, ?, ?) "
        "ON CONFLICT(ip) DO UPDATE SET reason = excluded.reason, until = excluded.until",
        (ip, reason, until),
    )

async def check_registration_rate_limit(ip: str, limit_per_day: int = 3) -> bool:
    today = date.today().isoformat()
    row = await fetch_one(
        "SELECT count FROM registration_ip WHERE ip = ? AND day = ?", (ip, today)
    )
    if row and row["count"] >= limit_per_day:
        return False
    return True

async def increment_registration_ip(ip: str):
    today = date.today().isoformat()
    await execute_query(
        "INSERT INTO registration_ip (ip, day, count) VALUES (?, ?, 1) "
        "ON CONFLICT(ip, day) DO UPDATE SET count = count + 1",
        (ip, today),
    )

async def record_login_attempt(ip: str, username: str, success: bool):
    await execute_query(
        "INSERT INTO login_attempt (ip, username, success, created_at) VALUES (?, ?, ?, ?)",
        (ip, username, int(success), datetime.utcnow().isoformat()),
    )

async def check_login_bruteforce(ip: str, window_minutes: int = 15, max_failures: int = 5) -> bool:
    cutoff = (datetime.utcnow() - timedelta(minutes=window_minutes)).isoformat()
    row = await fetch_one(
        "SELECT COUNT(*) as cnt FROM login_attempt "
        "WHERE ip = ? AND success = 0 AND created_at >= ?",
        (ip, cutoff),
    )
    return (row["cnt"] if row else 0) >= max_failures

async def record_download_once(app_id: int, user_ip: str) -> bool:
    if not user_ip:
        return False
    try:
        await execute_query(
            "INSERT INTO download_ip (app_id, ip, created_at) VALUES (?, ?, ?)",
            (app_id, user_ip, datetime.utcnow().isoformat()),
        )
    except Exception:
        return False
    await execute_query(
        "UPDATE apps SET data = json_set(data, '$.downloads', "
        "COALESCE(json_extract(data, '$.downloads'), 0) + 1) WHERE id = ?",
        (app_id,),
    )
    return True
