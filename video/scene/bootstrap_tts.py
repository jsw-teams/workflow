"""Verify the vendored MIT speech bridge; no clone or credentials needed."""
import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parents[2]/'third_party/tts'
manifest=json.loads((root/'UPSTREAM.json').read_text(encoding='utf-8'))
for name,digest in manifest['files'].items():
    if hashlib.sha256((root/name).read_bytes()).hexdigest()!=digest:
        raise SystemExit('Vendored speech source hash mismatch: '+name)
print('Vendored speech source verified at '+manifest['commit'])
