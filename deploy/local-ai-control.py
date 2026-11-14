"""Enable/disable this instance's optional AI UI, preserving other environment keys."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('action', choices=['enable', 'disable'])
args = parser.parse_args()
path = Path(__file__).resolve().parent.parent / '.env'
info = path.stat()
lines = [line for line in path.read_text().splitlines() if line.partition('=')[0].strip() != 'TOOLBOX_LOCAL_AI']
lines.append('TOOLBOX_LOCAL_AI=' + ('1' if args.action == 'enable' else '0'))
fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.local-ai-')
try:
    with os.fdopen(fd, 'w', encoding='utf-8') as output: output.write('\n'.join(lines) + '\n')
    os.chmod(temporary, 0o600)
    if os.geteuid() == 0: os.chown(temporary, info.st_uid, info.st_gid)
    os.replace(temporary, path)
finally:
    if os.path.exists(temporary): os.unlink(temporary)
subprocess.run(['sudo', '-n', 'systemctl', 'restart', 'toolbox'], check=True)
print('Essai IA active.' if args.action == 'enable' else 'Essai IA desactive.')
