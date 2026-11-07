"""Email accounts lifecycle; isolated DB, dummy passwords, mocked SMTP only."""
import tempfile
import time
import sqlite3
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from app import accounts, auth, config, ratelimit, mail, email_accounts
from app.main import app


class AccountTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'accounts.sqlite3'
        self.password='Unique test passphrase 2026';self.owner_password='Owner password for tests only'
        self.patches=[patch.object(accounts,'DB_PATH',self.path),patch.object(config,'USERNAME','owner'),patch.object(config,'PASSWORD_HASH',auth.hash_password(self.owner_password)),patch.object(mail,'ready',return_value=True),patch.object(mail,'send_link')]
        for p in self.patches:p.start()
        self.send=mail.send_link;auth._sessions.clear();ratelimit._attempts.clear()
        self.client=TestClient(app,base_url='https://testserver');self.headers={'X-Toolbox-Request':'1'}

    def tearDown(self):
        self.client.close()
        for p in reversed(self.patches):p.stop()
        auth._sessions.clear();ratelimit._attempts.clear();self.temp.cleanup()

    def post(self,path,payload):return self.client.post('/api/'+path,headers=self.headers,json=payload)
    def login(self,name='owner',password=None):return self.post('login',{'username':name,'password':password or self.owner_password})
    def signup(self,email='guest@example.org'):
        accounts.set_enabled(True)
        return self.post('register',{'email':email,'password':self.password})
    def verify(self):
        token=self.send.call_args.args[1]
        return self.post('account/confirm',{'purpose':'verify','token':token,'password':self.password})
    def decision(self,user,action):return self.post('admin/accounts',{'username':user,'action':action,'password':self.owner_password})
    def approved(self):
        self.signup();self.verify();user=accounts.dashboard()['accounts'][0]['username'];self.login();self.decision(user,'approve');return user

    def test_approval_email_login_privilege_and_reactivation(self):
        self.assertEqual(self.signup().status_code,200)
        user=accounts.dashboard()['accounts'][0]['username'];self.login()
        self.assertEqual(self.decision(user,'approve').status_code,409)
        self.assertEqual(self.verify().status_code,200)
        self.assertEqual(self.login('guest@example.org',self.password).status_code,401)
        self.assertEqual(self.decision(user,'approve').status_code,200)
        self.assertGreater(accounts.dashboard()['accounts'][0]['expires'],time.time()+365*86400)
        self.assertEqual(self.login('GUEST@example.org',self.password).status_code,200)
        cookie=self.client.cookies.get(config.SESSION_COOKIE)
        self.assertEqual(self.client.get('/api/admin/accounts').status_code,403)
        self.assertEqual(self.client.get('/api/admin/load').status_code,403)
        self.assertEqual(self.post('admin/registration',{'enabled':True,'password':self.owner_password}).status_code,403)
        self.login();self.assertEqual(self.decision(user,'suspend').status_code,200)
        self.assertIsNone(auth.get_session_user(cookie))
        self.assertEqual(self.decision(user,'reactivate').status_code,200)
        self.assertIsNone(auth.get_session_user(cookie))
        self.assertEqual(self.login('guest@example.org',self.password).status_code,200)

    def test_reset_single_use_expiry_and_session_revocation(self):
        user=self.approved();self.login('guest@example.org',self.password);cookie=self.client.cookies.get(config.SESSION_COOKIE)
        response=self.post('account/email-link',{'email':'guest@example.org','purpose':'reset'});self.assertEqual(response.status_code,200)
        token=self.send.call_args.args[1]
        with accounts.database() as db:self.assertNotEqual(db.execute('SELECT digest FROM mail_tokens').fetchone()[0],token)
        new='A replacement passphrase 2026'
        payload={'purpose':'reset','token':token,'password':new}
        self.assertEqual(self.post('account/confirm',payload).status_code,200)
        self.assertIsNone(auth.get_session_user(cookie))
        self.assertEqual(self.post('account/confirm',payload).status_code,400)
        self.assertEqual(self.login('guest@example.org',self.password).status_code,401)
        self.assertEqual(self.login('guest@example.org',new).status_code,200)
        self.post('account/email-link',{'email':'guest@example.org','purpose':'reset'});token=self.send.call_args.args[1]
        with accounts.database() as db:db.execute('UPDATE mail_tokens SET expires=0')
        self.assertEqual(self.post('account/confirm',{'purpose':'reset','token':token,'password':new}).status_code,400)

    def test_generic_responses_and_duplicates(self):
        first=self.signup();second=self.signup('GUEST@example.org');self.assertEqual(first.json(),second.json())
        self.assertEqual(len(accounts.dashboard()['accounts']),1)
        existing=self.post('account/email-link',{'email':'guest@example.org','purpose':'reset'})
        absent=self.post('account/email-link',{'email':'absent@example.org','purpose':'reset'})
        self.assertEqual(existing.json(),absent.json())
        self.assertEqual(self.signup('not-an-email').status_code,400)
        self.assertEqual(self.post('register',{'email':'x@example.org','password':'short'}).status_code,422)

    def test_reauth_csrf_delete_and_mail_configuration(self):
        user=self.approved()
        self.assertEqual(self.post('admin/accounts',{'username':user,'action':'suspend','password':'wrong'}).status_code,403)
        self.assertEqual(self.client.post('/api/admin/accounts',json={'username':user,'action':'suspend','password':self.owner_password}).status_code,403)
        self.assertEqual(self.decision(user,'delete').status_code,409)
        self.decision(user,'suspend');self.assertEqual(self.decision(user,'delete').status_code,200)
        self.assertIsNone(accounts.active(user))
        with patch.object(mail,'ready',return_value=False):
            self.assertFalse(self.client.get('/api/registration').json()['enabled'])
            self.assertEqual(self.signup('new@example.org').status_code,503)
            self.assertEqual(self.post('admin/registration',{'enabled':True,'password':self.owner_password}).status_code,503)

    def test_failed_mail_and_rate_limit(self):
        with patch.object(mail,'send_link',side_effect=RuntimeError('SMTP unavailable')):
            self.signup()
        with accounts.database() as db:self.assertEqual(db.execute('SELECT count(*) FROM mail_tokens').fetchone()[0],0)
        for _ in range(5):self.post('account/email-link',{'email':'guest@example.org','purpose':'verify'})
        self.assertEqual(self.post('account/email-link',{'email':'guest@example.org','purpose':'verify'}).status_code,429)
        self.assertLessEqual(self.send.call_count,2)

    def test_legacy_migration_and_email_link(self):
        with sqlite3.connect(self.path) as db:
            db.execute('CREATE TABLE accounts(username TEXT PRIMARY KEY COLLATE NOCASE,password_hash TEXT NOT NULL,status TEXT NOT NULL,created REAL NOT NULL,expires REAL NOT NULL)')
            db.execute("INSERT INTO accounts VALUES ('legacy',?,'active',?,?)",(auth.hash_password(self.password),time.time(),time.time()+1000))
        self.assertIsNotNone(accounts.active('legacy'))
        self.assertGreater(accounts.dashboard()['accounts'][0]['expires'],time.time()+365*86400)
        self.assertEqual(self.login('legacy',self.password).status_code,200)
        self.assertEqual(self.post('account/link-email',{'email':'old@example.org','password':'wrong'}).status_code,403)
        self.assertEqual(self.post('account/link-email',{'email':'old@example.org','password':self.password}).status_code,200)
        self.assertEqual(self.verify().status_code,200)
        self.assertEqual(self.login('old@example.org',self.password).status_code,200)


    def test_cannot_activate_unverified_or_verify_without_password(self):
        self.signup();token=self.send.call_args.args[1];user=accounts.dashboard()['accounts'][0]['username']
        self.assertEqual(self.post('account/confirm',{'purpose':'verify','token':token,'password':'Wrong password long enough'}).status_code,400)
        self.login();self.decision(user,'suspend')
        self.assertEqual(self.decision(user,'reactivate').status_code,409)
        self.assertIsNone(accounts.active(user))
