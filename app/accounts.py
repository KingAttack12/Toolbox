"""Small, persistent approval beta. Owner identity stays in server configuration."""
import re
import sqlite3
import time
from contextlib import contextmanager, closing
from fastapi import HTTPException
from . import config

DB_PATH = config.BASE_DIR / "data" / "accounts.sqlite3"

@contextmanager
def database():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(DB_PATH, timeout=10)) as db, db:
        db.row_factory = sqlite3.Row
        db.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        db.execute("CREATE TABLE IF NOT EXISTS accounts (username TEXT PRIMARY KEY COLLATE NOCASE, password_hash TEXT NOT NULL, status TEXT NOT NULL, created REAL NOT NULL, expires REAL NOT NULL)")
        db.execute("CREATE TABLE IF NOT EXISTS audit (id INTEGER PRIMARY KEY, username TEXT NOT NULL, action TEXT NOT NULL, created REAL NOT NULL)")
        db.execute("DELETE FROM accounts WHERE expires < ?", (time.time(),))
        db.execute("DELETE FROM audit WHERE created < ?", (time.time()-30*86400,))
        db.commit()
        yield db


def enabled():
    with database() as db:
        row = db.execute("SELECT value FROM settings WHERE key='registration'").fetchone()
        return bool(row and row[0] == "1")


def active(username):
    with database() as db:
        return db.execute("SELECT password_hash FROM accounts WHERE username=? AND status='active'", (username,)).fetchone()


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
        db.execute("INSERT OR IGNORE INTO accounts VALUES (?, ?, 'pending', ?, ?)", (username, password_hash, time.time(), time.time()+7*86400))


def dashboard():
    with database() as db:
        users = [dict(r) for r in db.execute("SELECT username,status,created,expires FROM accounts ORDER BY created DESC")]
        audit = [dict(r) for r in db.execute("SELECT username,action,created FROM audit ORDER BY id DESC LIMIT 30")]
    return {"enabled": enabled(), "accounts": users, "audit": audit}


def set_enabled(value):
    with database() as db:
        db.execute("INSERT OR REPLACE INTO settings VALUES ('registration', ?)", ("1" if value else "0",))
        db.execute("INSERT INTO audit(username,action,created) VALUES (?,?,?)", (config.USERNAME, "Ouverture des demandes" if value else "Fermeture des demandes", time.time()))


def decide(username, action):
    with database() as db:
        row = db.execute("SELECT status FROM accounts WHERE username=?", (username,)).fetchone()
        if not row:
            raise HTTPException(404, "Compte introuvable ou expiré.")
        if action == "approve" and row[0] != "pending":
            raise HTTPException(409, "Cette demande a déjà été traitée.")
        state = {"approve": "active", "reject": "rejected", "suspend": "suspended"}[action]
        if state == "active":
            db.execute("UPDATE accounts SET status=?,expires=? WHERE username=?", (state, time.time()+7*86400, username))
        else:
            db.execute("UPDATE accounts SET status=?,password_hash='' WHERE username=?", (state, username))
        db.execute("INSERT INTO audit(username,action,created) VALUES (?,?,?)", (username, state, time.time()))
