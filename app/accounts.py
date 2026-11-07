"""Small, persistent approval beta. Owner identity stays in server configuration."""
import re
import threading
_schema_lock = threading.RLock()
import sqlite3
import time
from contextlib import contextmanager, closing
from fastapi import HTTPException
from . import config

DB_PATH = config.BASE_DIR / "data" / "accounts.sqlite3"

@contextmanager
def database():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _schema_lock, closing(sqlite3.connect(DB_PATH, timeout=10)) as db, db:
        db.row_factory = sqlite3.Row
        db.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        db.execute("CREATE TABLE IF NOT EXISTS accounts (username TEXT PRIMARY KEY COLLATE NOCASE, password_hash TEXT NOT NULL, status TEXT NOT NULL, created REAL NOT NULL, expires REAL NOT NULL)")
        db.execute("CREATE TABLE IF NOT EXISTS audit (id INTEGER PRIMARY KEY, username TEXT NOT NULL, action TEXT NOT NULL, created REAL NOT NULL)")
        columns = {r[1] for r in db.execute("PRAGMA table_info(accounts)")}
        if "email" not in columns:
            db.execute("ALTER TABLE accounts ADD COLUMN email TEXT COLLATE NOCASE")
            db.execute("ALTER TABLE accounts ADD COLUMN verified INTEGER NOT NULL DEFAULT 0")
            db.execute("ALTER TABLE accounts ADD COLUMN last_login REAL")
            db.execute("ALTER TABLE accounts ADD COLUMN version INTEGER NOT NULL DEFAULT 0")
            db.execute("UPDATE accounts SET expires=253402300799 WHERE status='active' AND expires>?", (time.time(),))
        db.execute("CREATE UNIQUE INDEX IF NOT EXISTS account_email ON accounts(email) WHERE email IS NOT NULL")
        db.execute("CREATE TABLE IF NOT EXISTS mail_tokens (digest TEXT PRIMARY KEY, username TEXT NOT NULL, purpose TEXT NOT NULL, expires REAL NOT NULL)")
        db.execute("CREATE TABLE IF NOT EXISTS mail_limits (target TEXT NOT NULL, created REAL NOT NULL)")
        db.execute("DELETE FROM accounts WHERE expires < ?", (time.time(),))
        db.execute("DELETE FROM mail_tokens WHERE expires < ? OR username NOT IN (SELECT username FROM accounts)", (time.time(),))
        db.execute("DELETE FROM mail_limits WHERE created < ?", (time.time()-3600,))
        db.execute("DELETE FROM audit WHERE created < ?", (time.time()-30*86400,))
        db.commit()
        yield db


def enabled():
    with database() as db:
        row = db.execute("SELECT value FROM settings WHERE key='registration'").fetchone()
        return bool(row and row[0] == "1")


def active(username):
    with database() as db:
        return db.execute("SELECT password_hash,version FROM accounts WHERE username=? AND status='active'", (username,)).fetchone()


def request_account(username, password_hash):
    with database() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT value FROM settings WHERE key='registration'").fetchone()
        if not row or row[0] != "1":
            raise HTTPException(403, "Les demandes de compte sont fermées.")
        count = db.execute("SELECT count(*) FROM accounts").fetchone()[0]
        if count >= 20:
            raise HTTPException(429, "Le test a atteint sa capacité. Réessayez plus tard.")
        if username.casefold() == config.USERNAME.casefold():
            return
        db.execute("INSERT OR IGNORE INTO accounts(username,password_hash,status,created,expires) VALUES (?, ?, 'pending', ?, ?)", (username, password_hash, time.time(), time.time()+7*86400))


def dashboard():
    with database() as db:
        users = [dict(r) for r in db.execute("SELECT username,email,verified,status,created,expires,last_login FROM accounts ORDER BY created DESC")]
        if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='conversion_usage'").fetchone():
            usage = dict(db.execute("SELECT username,count(*) FROM conversion_usage WHERE created>? GROUP BY username", (time.time()-3600,)))
        else: usage = {}
        for account in users: account["conversions_hour"] = usage.get(account["username"].casefold(), 0)
        audit = [dict(r) for r in db.execute("SELECT username,action,created FROM audit ORDER BY id DESC LIMIT 30")]
    from . import mail
    return {"enabled": enabled(), "accounts": users, "audit": audit, "mail_ready": mail.ready()}


def set_enabled(value):
    with database() as db:
        db.execute("INSERT OR REPLACE INTO settings VALUES ('registration', ?)", ("1" if value else "0",))
        db.execute("INSERT INTO audit(username,action,created) VALUES (?,?,?)", (config.USERNAME, "Ouverture des demandes" if value else "Fermeture des demandes", time.time()))


def decide(username, action):
    with database() as db:
        row = db.execute("SELECT status,email,verified FROM accounts WHERE username=?", (username,)).fetchone()
        if not row:
            raise HTTPException(404, "Compte introuvable ou expiré.")
        if action in ("approve", "reactivate") and row["email"] and not row["verified"]:
            raise HTTPException(409, "L’adresse e-mail doit être confirmée avant activation.")
        if action == "approve" and row[0] != "pending":
            raise HTTPException(409, "Cette demande a déjà été traitée.")
        if action == "delete":
            if row[0] not in ("rejected", "suspended"):raise HTTPException(409,"Suspendez ou refusez d’abord ce compte.")
            db.execute("DELETE FROM accounts WHERE username=?",(username,))
            db.execute("DELETE FROM mail_tokens WHERE username=?",(username,))
            db.execute("INSERT INTO audit(username,action,created) VALUES (?,?,?)",(username,"Compte supprimé",time.time()))
            return
        state = {"approve": "active", "reject": "rejected", "suspend": "suspended", "reactivate": "active"}[action]
        if action == "reactivate" and row[0] != "suspended":
            raise HTTPException(409, "Seul un compte suspendu peut être réactivé.")
        if state == "active":
            db.execute("UPDATE accounts SET status=?,expires=? WHERE username=?", (state, 253402300799, username))
        else:
            db.execute("UPDATE accounts SET status=? WHERE username=?", (state, username))
            if state == "rejected": db.execute("UPDATE accounts SET password_hash='' WHERE username=?", (username,))
        db.execute("UPDATE accounts SET version=version+1 WHERE username=?", (username,))
        db.execute("DELETE FROM mail_tokens WHERE username=?", (username,))
        db.execute("INSERT INTO audit(username,action,created) VALUES (?,?,?)", (username, state, time.time()))
