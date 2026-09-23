"""Génère un hash PBKDF2 à mettre dans .env (ne jamais commiter le .env réel)."""
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.auth import hash_password  # noqa: E402

if __name__ == "__main__":
    print("=== Toolbox : génération du hash mot de passe ===")
    pwd = getpass.getpass("Nouveau mot de passe (min 8 caractères) : ")
    pwd2 = getpass.getpass("Confirmer : ")
    if pwd != pwd2:
        print("ERREUR : les mots de passe diffèrent.")
        raise SystemExit(1)
    try:
        h = hash_password(pwd)
    except ValueError as e:
        print(f"ERREUR : {e}")
        raise SystemExit(1)
    print("\nCopiez cette ligne dans votre fichier .env :\n")
    print(f"TOOLBOX_PASSWORD_HASH={h}")
    print("\nPuis redémarrez le serveur.")
