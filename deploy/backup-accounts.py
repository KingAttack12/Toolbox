"""Run on the server before migration. Writes a private, consistent SQLite backup."""
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
root=Path(__file__).resolve().parent.parent
source=root/'data'/'accounts.sqlite3'
if not source.exists():raise SystemExit('No accounts database to back up')
folder=root/'data'/'backups';folder.mkdir(parents=True,exist_ok=True);folder.chmod(0o700)
output=folder/('accounts-'+datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')+'.sqlite3')
with closing(sqlite3.connect(source)) as src, closing(sqlite3.connect(output)) as dst:src.backup(dst)
output.chmod(0o600)
print('Account database backed up successfully')
