"""Guard against accidental changes between sequential mode runs."""
import hashlib
import json
from pathlib import Path
root=Path('/data/users/taslab_zxp')
output=root/'outputs/GLIO/Deep-Urban-1/Comparison_calibrated_v2'
p=json.loads((output/'protocol.json').read_text())
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
for name,item in p['assets'].items():
    path=Path(item['path']); stat=path.stat()
    assert stat.st_size==item['bytes'] and stat.st_mtime_ns==item['mtime_ns'],name
    if path.suffix!='.bag': assert sha(path)==item['sha256'],name
for relative,digest in p['source_files'].items():
    assert sha(root/'projects/GLIO_ws/src/GLIO'/relative)==digest,relative
assert sha(p['estimator_binary']['path'])==p['estimator_binary']['sha256']
image=Path(p['container']['path']).stat()
assert image.st_size==p['container']['bytes'] and image.st_mtime_ns==p['container']['mtime_ns']
profile=root/'projects/GLIO_setup/profiles/calibrated_v2'
assert sha(profile/'manifest.json')==p['profile_manifest_sha256']
for mode,values in p['configs'].items():
    for kind in ['yaml','launch']:
        assert sha(profile/'configs'/(mode+'.'+kind))==values[kind]
print('Frozen data, code, executable, initialization and calibration checks passed')
