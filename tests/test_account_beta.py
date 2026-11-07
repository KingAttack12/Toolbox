"""Isolated tests: never use the real account database or owner credentials."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from app import accounts, auth, config, ratelimit
from app.main import app


class AccountBetaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.patches = [patch.object(accounts, "DB_PATH", Path(self.temp.name)/"accounts.sqlite3"), patch.object(config, "USERNAME", "owner"), patch.object(config, "PASSWORD_HASH", auth.hash_password("Owner test password only"))]
        for p in self.patches: p.start()
        auth._sessions.clear(); ratelimit._attempts.clear()
        self.client = TestClient(app, base_url="https://testserver")
        self.headers = {"X-Toolbox-Request": "1"}
        self.password = "Unique test passphrase 2026"

    def tearDown(self):
        self.client.close()
        for p in reversed(self.patches): p.stop()
        auth._sessions.clear(); ratelimit._attempts.clear()
        self.temp.cleanup()

    def owner(self):
        response = self.client.post("/api/login", json={"username":"owner", "password":"Owner test password only"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("Secure", response.headers["set-cookie"])
        return response

    def signup(self, name="guest"):
        return self.client.post("/api/register", headers=self.headers, json={"username":name,"password":self.password})

    def test_approval_privileges_revocation_and_logout(self):
        self.assertFalse(self.client.get("/api/registration").json()["enabled"])
        self.assertEqual(self.signup().status_code,403)
        self.assertEqual(self.client.get("/api/admin/accounts").status_code,401)
        self.owner()
        self.assertEqual(self.client.post("/api/admin/registration",json={"enabled":True}).status_code,403)
        self.assertEqual(self.client.post("/api/admin/registration",headers=self.headers,json={"enabled":True}).status_code,200)
        self.assertEqual(self.signup().status_code,200)
        self.assertEqual(self.signup().status_code,200)
        owner_cookie=self.client.cookies.get(config.SESSION_COOKIE)
        self.assertEqual(self.client.post("/api/login",json={"username":"guest","password":self.password}).status_code,401)
        self.assertEqual(self.client.post("/api/admin/accounts",headers=self.headers,json={"username":"guest","action":"approve"}).status_code,200)
        listing=self.client.get("/api/admin/accounts").text
        self.assertNotIn(self.password,listing); self.assertNotIn("password_hash",listing)
        self.assertEqual(self.client.post("/api/login",json={"username":"GUEST","password":self.password}).status_code,200)
        guest_cookie=self.client.cookies.get(config.SESSION_COOKIE)
        self.assertEqual(self.client.get("/api/me").json()["is_admin"],False)
        self.assertEqual(self.client.get("/api/admin/accounts").status_code,403)
        self.assertEqual(self.client.post("/api/admin/accounts",headers=self.headers,json={"username":"guest","action":"approve"}).status_code,403)
        self.client.cookies.clear(); self.owner()
        owner_cookie=self.client.cookies.get(config.SESSION_COOKIE)
        self.assertEqual(self.client.post("/api/admin/accounts",headers=self.headers,json={"username":"guest","action":"suspend"}).status_code,200)
        self.assertIsNone(auth.get_session_user(guest_cookie))
        self.assertEqual(self.client.post("/api/logout").status_code,200)
        self.assertIsNone(auth.get_session_user(owner_cookie))

    def test_validation_rate_limits_and_csrf(self):
        accounts.set_enabled(True)
        self.assertEqual(self.client.post("/api/register",json={"username":"guest","password":self.password}).status_code,403)
        self.assertEqual(self.client.post("/api/register",headers={**self.headers,"sec-fetch-site":"cross-site"},json={"username":"guest","password":self.password}).status_code,403)
        self.assertEqual(self.signup("../bad").status_code,400)
        self.assertEqual(self.client.post("/api/register",headers=self.headers,json={"username":"guest","password":"short"}).status_code,422)
        for n in range(4): self.assertEqual(self.signup("user"+str(n)).status_code,200)
        self.assertEqual(self.signup("limited").status_code,429)

    def test_capacity_and_duplicate_preserves_password(self):
        accounts.set_enabled(True)
        accounts.request_account("guest", auth.hash_password(self.password))
        accounts.request_account("GUEST", auth.hash_password("Another passphrase for test"))
        accounts.decide("guest", "approve")
        self.assertTrue(auth.check_credentials("guest", self.password))
        self.assertFalse(auth.check_credentials("guest", "Another passphrase for test"))
        for n in range(19): accounts.request_account("test"+str(n), "unused-test-hash")
        self.assertEqual(self.signup("overflow").status_code,429)

    def test_expiry_rejection_and_owner_reservation(self):
        accounts.set_enabled(True)
        self.signup("OWNER"); self.assertEqual(accounts.dashboard()["accounts"],[])
        self.signup(); accounts.decide("guest","reject")
        self.assertIsNone(accounts.active("guest"))
        self.signup("expires"); accounts.decide("expires","approve")
        token=auth.create_session("expires")
        with accounts.database() as db: db.execute("UPDATE accounts SET expires=0 WHERE username='expires'")
        self.assertIsNone(auth.get_session_user(token))
        with accounts.database() as db: self.assertEqual(db.execute("SELECT password_hash FROM accounts WHERE username='guest'").fetchone()[0], "")


if __name__ == "__main__": unittest.main()
