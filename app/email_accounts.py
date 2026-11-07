"""Email identity lifecycle, verification and recovery with one-use tokens."""
import hashlib
import logging
import re
import secrets
import time
from fastapi import HTTPException
from . import accounts, config, mail


def normalize(email):
    email=email.strip().lower()
    if len(email)>254 or not re.fullmatch(r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]{1,64}@[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+",email):
        raise HTTPException(400,"Saisissez une adresse e-mail valide.")
    return email


def resolve(identity):
    if '@' not in identity: return identity
    with accounts.database() as db:
        row=db.execute("SELECT username FROM accounts WHERE email=? AND verified=1",(identity.strip().lower(),)).fetchone()
    return row[0] if row else ""


def register(email,password_hash):
    if not mail.ready():raise HTTPException(503,"Les inscriptions par e-mail ne sont pas encore disponibles.")
    if not accounts.enabled():raise HTTPException(403,"Les demandes de compte sont fermées.")
    with accounts.database() as db:
        db.execute("BEGIN IMMEDIATE")
        if db.execute("SELECT 1 FROM accounts WHERE email=?",(email,)).fetchone():return
        if db.execute("SELECT count(*) FROM accounts").fetchone()[0]>=20:raise HTTPException(429,"Capacité des comptes atteinte. Contactez le propriétaire.")
        db.execute("INSERT INTO accounts(username,password_hash,status,created,expires,email) VALUES (?,?,'unverified',?,?,?)",('user_'+secrets.token_hex(10),password_hash,time.time(),time.time()+7*86400,email))


def send_requested_link(email,purpose):
    # Background task: API replies don't reveal whether the mailbox exists.
    token=None
    with accounts.database() as db:
        db.execute("BEGIN IMMEDIATE")
        target=hashlib.sha256(email.encode()).hexdigest()
        if db.execute("SELECT count(*) FROM mail_limits").fetchone()[0]>=60:return
        if db.execute("SELECT count(*) FROM mail_limits WHERE target=?",(target,)).fetchone()[0]>=3:return
        db.execute("INSERT INTO mail_limits VALUES (?,?)",(target,time.time()))
        row=db.execute("SELECT username,status,verified FROM accounts WHERE email=?",(email,)).fetchone()
        eligible=row and ((purpose=='verify' and not row['verified'] and row['status'] in ('unverified','active')) or (purpose=='reset' and row['verified'] and row['status']=='active'))
        if not eligible:return
        token=secrets.token_urlsafe(32);digest=hashlib.sha256(token.encode()).hexdigest()
        db.execute("DELETE FROM mail_tokens WHERE username=? AND purpose=?",(row['username'],purpose))
        db.execute("INSERT INTO mail_tokens VALUES (?,?,?,?)",(digest,row['username'],purpose,time.time()+(86400 if purpose=='verify' else 1800)))
    try:mail.send_link(email,token,purpose)
    except Exception:
        logging.getLogger(__name__).warning("Transactional email delivery failed; inspect SMTP configuration.")
        with accounts.database() as db:
            db.execute("DELETE FROM mail_tokens WHERE digest=?",(digest,))
            db.execute("INSERT INTO audit(username,action,created) VALUES (?,?,?)",(row['username'],'Échec envoi e-mail',time.time()))


def consume(token,purpose,password_hash=None,verification_password=None):
    digest=hashlib.sha256(token.encode()).hexdigest()
    with accounts.database() as db:
        db.execute("BEGIN IMMEDIATE")
        row=db.execute("SELECT t.username,a.status,a.verified,a.password_hash FROM mail_tokens t JOIN accounts a ON a.username=t.username WHERE t.digest=? AND t.purpose=? AND t.expires>?",(digest,purpose,time.time())).fetchone()
        if not row:raise HTTPException(400,"Lien invalide ou expiré. Demandez un nouveau lien.")
        user=row['username']
        if purpose=='verify':
            from .auth import verify_password
            if not verification_password or not verify_password(verification_password,row['password_hash']):raise HTTPException(400,'Confirmez le mot de passe choisi pour ce compte.')
            if row['status'] not in ('unverified','active'):raise HTTPException(400,"Ce compte ne peut pas être confirmé.")
            db.execute("UPDATE accounts SET verified=1,status=CASE WHEN status='unverified' THEN 'pending' ELSE status END WHERE username=?",(user,))
        else:
            if row['status']!='active' or not row['verified']:raise HTTPException(400,"Lien invalide ou expiré.")
            db.execute("UPDATE accounts SET password_hash=?,version=version+1 WHERE username=?",(password_hash,user))
        db.execute("DELETE FROM mail_tokens WHERE username=?",(user,))
        db.execute("INSERT INTO audit(username,action,created) VALUES (?,?,?)",(user,'Adresse confirmée' if purpose=='verify' else 'Mot de passe réinitialisé',time.time()))


def link_legacy(user,email):
    with accounts.database() as db:
        db.execute("BEGIN IMMEDIATE")
        row=db.execute("SELECT email FROM accounts WHERE username=?",(user,)).fetchone()
        if not row or row['email']:raise HTTPException(409,"Ce compte possède déjà une adresse ou ne peut pas être migré.")
        if db.execute("SELECT 1 FROM accounts WHERE email=?",(email,)).fetchone():raise HTTPException(409,"Cette adresse ne peut pas être utilisée.")
        db.execute("UPDATE accounts SET email=? WHERE username=?",(email,user))
