"""Interactive Gmail setup over SSH; no password in arguments, logs or Git."""
import argparse
import getpass
import os
import re
import smtplib
import ssl
import subprocess
import tempfile
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('--email')
parser.add_argument('--prepare', action='store_true')
args=parser.parse_args()
root=Path(__file__).resolve().parent.parent
path=root/'.env'
existing=dict(line.split('=',1) for line in path.read_text(encoding='utf-8').splitlines() if '=' in line and not line.lstrip().startswith('#'))
email=(args.email or existing.get('TOOLBOX_SMTP_USER','')).strip().lower()
if not re.fullmatch(r'[a-z0-9._+%-]+@gmail\.com',email):raise SystemExit('Adresse Gmail invalide ou absente.')
settings={'TOOLBOX_PUBLIC_URL':'https://mytoolbox.duckdns.org','TOOLBOX_SMTP_HOST':'smtp.gmail.com','TOOLBOX_SMTP_PORT':'587','TOOLBOX_SMTP_USER':email,'TOOLBOX_SMTP_FROM':email}
if not args.prepare:
    password=getpass.getpass("Mot de passe d'application Google (saisie masquee) : ").replace(' ','')
    if not re.fullmatch(r'[A-Za-z]{16}',password):raise SystemExit("Format inattendu : utilisez le mot de passe d'application Google de 16 lettres.")
    try:
        with smtplib.SMTP('smtp.gmail.com',587,timeout=20) as smtp:
            smtp.ehlo();smtp.starttls(context=ssl.create_default_context());smtp.ehlo();smtp.login(email,password)
    except Exception:
        raise SystemExit('Connexion Gmail refusee ou indisponible. Aucun changement enregistre.')
    settings['TOOLBOX_SMTP_PASSWORD']=password
lines=path.read_text(encoding='utf-8').splitlines()
# Remove all copies of configured keys, keeping every other setting intact.
lines=[line for line in lines if line.partition('=')[0].strip() not in settings]
lines += [key+'='+value for key,value in settings.items()]
fd,temp=tempfile.mkstemp(prefix='.smtp-',dir=root)
try:
    with os.fdopen(fd,'w',encoding='utf-8') as f:f.write('\n'.join(lines)+'\n')
    os.chmod(temp,0o600);os.replace(temp,path)
finally:
    if os.path.exists(temp):os.unlink(temp)
subprocess.run(['sudo','-n','systemctl','restart','toolbox'],check=True)
print('Adresse Gmail configuree. Mot de passe encore requis.' if args.prepare else 'Authentification Gmail reussie. Configuration enregistree et service redemarre. Aucun e-mail de test envoye.')
