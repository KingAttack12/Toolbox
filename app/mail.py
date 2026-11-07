"""TLS-only transactional mail. Never log credentials or token URLs."""
import smtplib
import ssl
from email.message import EmailMessage
from . import config


def ready():
    return bool(config.SMTP_HOST and config.SMTP_USER and config.SMTP_PASSWORD and config.SMTP_FROM and config.PUBLIC_URL.startswith("https://") and config.SMTP_PORT in (465,587))


def send_link(email, token, purpose):
    if not ready(): raise RuntimeError("Mail unavailable")
    msg=EmailMessage();msg["From"]=config.SMTP_FROM;msg["To"]=email
    msg["Subject"]="Toolbox — " + ("confirmez votre adresse" if purpose=="verify" else "réinitialisez votre mot de passe")
    action="Confirmez votre adresse avant validation par le propriétaire." if purpose=="verify" else "Choisissez un nouveau mot de passe."
    msg.set_content(action+"\n\n"+config.PUBLIC_URL+"/#"+purpose+"="+token+"\n\nLien à usage unique, valable "+("24 heures" if purpose=="verify" else "30 minutes")+". Si vous n’êtes pas à l’origine de cette demande, ignorez cet e-mail.")
    context=ssl.create_default_context()
    smtp=smtplib.SMTP_SSL(config.SMTP_HOST,config.SMTP_PORT,timeout=15,context=context) if config.SMTP_PORT==465 else smtplib.SMTP(config.SMTP_HOST,config.SMTP_PORT,timeout=15)
    with smtp:
        if config.SMTP_PORT==587:smtp.ehlo();smtp.starttls(context=context);smtp.ehlo()
        smtp.login(config.SMTP_USER,config.SMTP_PASSWORD);smtp.send_message(msg)
