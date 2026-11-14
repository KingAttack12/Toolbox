"""Synthetic local benchmark only. Never reads accounts or user documents."""
import json
from pathlib import Path
import sys
import threading
import time
from urllib.request import urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.routers.local_ai import generate, resources

stop = threading.Event()
samples, latencies, health_errors = [], [], []


def monitor():
    while not stop.is_set():
        samples.append(resources())
        started = time.monotonic()
        try:
            with urlopen('http://127.0.0.1:8000/api/health', timeout=3) as response:
                assert json.load(response)['ok']
            latencies.append(time.monotonic()-started)
        except Exception:
            health_errors.append(True)
        stop.wait(1)


worker = threading.Thread(target=monitor, daemon=True)
worker.start()
results = []
try:
    for mode, text in [
        ('correct', 'Les utilisateur peut convertir leur fichier en PDF. Cette outil est simple a utiliser et les resultat sont disponible apres le traitement.'),
        ('summary', 'Toolbox est un site privé qui rassemble des outils de conversion de documents, images, audio et vidéo. Les fichiers sont traités sur le serveur. Une file autorise un seul traitement lourd à la fois et trois demandes en attente. Les utilisateurs doivent confirmer leur adresse puis être approuvés par le propriétaire. Un panneau permet au propriétaire de surveiller la charge et de gérer les comptes. Le nouvel essai IA est réservé au propriétaire et limité aux textes courts. Il ne doit pas remplacer la vérification humaine des réponses.'),
    ]:
        result = generate(mode, text)
        result['mode'] = mode
        results.append(result)
        print(json.dumps(result, ensure_ascii=True), flush=True)
finally:
    stop.set(); worker.join(timeout=4)

report = {'results': results,
          'peak_memory_gib': round(max((entry['memory_used'] or 0 for entry in samples), default=0)/1024**3, 2),
          'health_max_ms': round(max(latencies, default=0)*1000, 1), 'health_failures': len(health_errors),
          'cpu_limit_cores': 1.5, 'memory_limit_gib': 4}
print(json.dumps(report, ensure_ascii=True), flush=True)
Path(__file__).resolve().parent.parent.joinpath('data/ai-benchmark.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
if health_errors or any(result['seconds'] > 90 for result in results):
    raise SystemExit('Essai trop lent ou site non reactif : ne pas activer.')
